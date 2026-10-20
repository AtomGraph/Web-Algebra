"""Write each example's README.md from an actual run.

    CERT_PEM_PATH=... CERT_PASSWORD=... uv run python scripts/document_examples.py [example ...]

Runs the example against LinkedDataHub (LDH_BASE, default
https://localhost:4443/) exactly as `pytest -m ldh tests/test_examples.py`
does, then reads back what the plan left there - the documents, their content
blocks in order, the other resources and data they hold - and writes it, with
the instruction, the plan's steps and the outcome of each expectation, to
examples/<example>/README.md. The example's container is removed afterwards.

The README states what one run produced; a run against live sources at another
time may differ in the details (counts, names), not in shape.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_examples import (  # noqa: E402
    EXAMPLES, _ask, _base, _expectations, _opener, _plans, _rebase, _remove, _request,
)
from web_algebra.main import LinkedDataHubSettings, list_operation_subclasses  # noqa: E402
from web_algebra.operation import Operation  # noqa: E402
import web_algebra.operations  # noqa: E402

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
SHORT = {
    "https://w3id.org/atomgraph/linkeddatahub#": "ldh:",
    "https://w3id.org/atomgraph/linkeddatahub/document-hierarchy#": "dh:",
    "http://spinrdf.org/sp#": "sp:",
    "http://www.w3.org/ns/sparql-service-description#": "sd:",
    "http://www.w3.org/2004/02/skos/core#": "skos:",
    "https://schema.org/": "schema:",
    "http://www.semanticdesktop.org/ontologies/2007/03/22/nfo#": "nfo:",
}


def short(uri: str) -> str:
    for ns, prefix in SHORT.items():
        if uri.startswith(ns):
            return prefix + uri[len(ns):]
    return uri


def select(opener, query: str, with_vars: bool = False):
    url = _base() + "sparql?" + urllib.parse.urlencode({"query": query})
    status, _, body = _request(opener, "GET", url, {"Accept": "application/sparql-results+json"})
    assert status == 200, body[:300]
    answer = json.loads(body)
    rows = [{k: v["value"] for k, v in row.items()} for row in answer["results"]["bindings"]]
    return (answer["head"]["vars"], rows) if with_vars else rows


def documents(opener, container: str) -> list:
    return [r["g"] for r in select(opener, f'SELECT DISTINCT ?g WHERE {{ GRAPH ?g {{ ?s ?p ?o }} FILTER(STRSTARTS(STR(?g), "{container}")) }} ORDER BY ?g')]


def describe(opener, doc: str, container: str) -> dict:
    title = select(opener, f"SELECT ?t WHERE {{ GRAPH <{doc}> {{ <{doc}> <http://purl.org/dc/terms/title> ?t }} }}")
    blocks = select(opener, f"""SELECT ?seq ?type ?value WHERE {{ GRAPH <{doc}> {{
        <{doc}> ?seq ?block . ?block a ?type OPTIONAL {{ ?block <{RDF}value> ?value }}
        FILTER(STRSTARTS(STR(?seq), "{RDF}_")) }} }}""")
    blocks.sort(key=lambda b: int(b["seq"].rsplit("_", 1)[1]))
    types = select(opener, f"""SELECT ?type (COUNT(DISTINCT ?s) AS ?n) WHERE {{ GRAPH <{doc}> {{ ?s a ?type
        FILTER(?s != <{doc}>) FILTER NOT EXISTS {{ <{doc}> ?seq ?s }} }} }} GROUP BY ?type ORDER BY ?type""")
    triples = select(opener, f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{doc}> {{ ?s ?p ?o }} }}")
    return {
        "doc": doc,
        "path": doc[len(container):] or "(container)",
        "title": title[0]["t"] if title else "",
        "blocks": [block_text(b, doc) for b in blocks],
        "resources": ", ".join(f'{t["n"]} {short(t["type"])}' for t in types),
        "triples": triples[0]["n"],
    }


def block_text(block: dict, doc: str) -> str:
    value = block.get("value", "")
    if block["type"].endswith("#XHTML"):
        text = " ".join(re.sub(r"<[^>]+>", " ", value).split())
        return f"text: “{text[:160]}{'…' if len(text) > 160 else ''}”"
    if value.startswith(doc + "#"):
        return f"`{value[len(doc):]}`"
    return f"<{value}>"


def cell(value: str, container: str) -> str:
    if value.startswith(container):
        return "`" + value[len(container):] + "`"
    return value


def steps(plan, depth=0) -> list:
    """The plan's top-level steps and the steps of the ForEach/Iterate bodies."""
    lines = []
    for node in plan if isinstance(plan, list) else [plan]:
        if not isinstance(node, dict) or "@op" not in node:
            continue
        name, args = node["@op"], node.get("args", {})
        if name == "Variable":
            inner = args.get("value", {})
            lines.append(f"{'  ' * depth}- `${args['name']}` ← {summary(inner)}")
        else:
            lines.append(f"{'  ' * depth}- {summary(node)}")
        if name in ("ForEach", "Iterate"):
            lines += steps(args.get("operation", []), depth + 1)
    return lines


def summary(node) -> str:
    if not isinstance(node, dict) or "@op" not in node:
        return "`" + json.dumps(node)[:60] + "`"
    ops = []

    def walk(n):
        if isinstance(n, dict):
            if "@op" in n and n["@op"] not in ("Value", "Filter", "Str", "Concat", "ResolveURI", "URI", "Current"):
                ops.append(n["@op"])
            for v in (n.get("args", {}) if "@op" in n else n).values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(node)
    head, rest = ops[0], [o for o in dict.fromkeys(ops[1:])]
    return f"`{head}`" + (f" (with {', '.join('`' + o + '`' for o in rest)})" if rest else "")


def operations_used(example: Path) -> list:
    found = set()
    for plan in _plans(example):
        found |= set(re.findall(r'"@op": "([^"]+)"', plan.read_text()))
    return sorted(found)


def ldh_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT.parent / "LinkedDataHub"), "log", "-1", "--format=%h"],
                              capture_output=True, text=True).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def document(example: Path, opener, settings) -> None:
    container = _base() + example.name + "/"
    _remove(opener, container)
    try:
        started = time.monotonic()
        for plan in _plans(example):
            Operation.process_json(settings, json.loads(_rebase(plan.read_text())))
        seconds = time.monotonic() - started
        checks = [(rq.stem, _ask(opener, _rebase(rq.read_text()))) for rq in _expectations(example)]
        docs = [describe(opener, d, container) for d in documents(opener, container)]
        columns, key = select(opener, _rebase((example / "result.rq").read_text()), with_vars=True) if (example / "result.rq").exists() else ([], [])
    finally:
        _remove(opener, container)

    plan = json.loads((example / "plan.json").read_text())
    out = [f"# {example.name}", "", "## Instruction", ""]
    out += ["> " + line if line else ">" for line in (example / "instruction.md").read_text().strip().splitlines()]
    out += ["", "## Plan", "", f"[`plan.json`](plan.json)"
            + (" runs after [`setup.json`](setup.json), which creates the starting state." if (example / "setup.json").exists() else "."),
            "", *steps(plan), "", "Operations used: " + ", ".join(f"`{o}`" for o in operations_used(example)) + ".", ""]
    out += ["## Result", "",
            f"From a run on {date.today().isoformat()} against LinkedDataHub {ldh_commit()} at `{_base()}`, "
            f"in {seconds:.1f} s. Counts and names come from the live sources and may differ on another day; "
            "the shape should not.", "",
            f"{len(docs)} documents under `{container}`:", "",
            "| Document | Title | Content blocks, in order | Other resources | Triples |",
            "|---|---|---|---|---|"]
    for d in docs:
        blocks = "<br>".join(f"{i}. {b}" for i, b in enumerate(d["blocks"], 1)) or "—"
        out.append(f"| `{d['path']}` | {d['title']} | {blocks} | {d['resources'] or '—'} | {d['triples']} |")
    if key:
        out += ["", f"Key data ([`result.rq`](result.rq)):", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        out += ["| " + " | ".join(cell(row.get(c, ""), container) for c in columns) + " |" for row in key]
    out += ["", "## Checks", "", "After the run, these hold on the instance ([`expect/`](expect/)):", ""]
    out += [f"- {'✅' if held else '❌'} `{name}`" for name, held in checks]
    out += ["", "## Run it", "", "With `CERT_PEM_PATH` and `CERT_PASSWORD` set to the LinkedDataHub owner certificate and its password:", "", "```bash",
            f"uv run web-algebra --from-json examples/{example.name}/plan.json",
            "```", "", "or with its checks, cleaning up after itself:", "", "```bash",
            f"uv run pytest -m ldh tests/test_examples.py -k {example.name}",
            "```", ""]
    if (example / "setup.json").exists():
        out[out.index("```bash") + 1:out.index("```bash") + 1] = [
            f"uv run web-algebra --from-json examples/{example.name}/setup.json"]
    (example / "README.md").write_text("\n".join(out))
    print(f"{example.name}: {len(docs)} documents, {sum(h for _, h in checks)}/{len(checks)} checks, {seconds:.1f} s")


def main(names: list) -> None:
    for c in list_operation_subclasses(web_algebra.operations, Operation):
        Operation.register(c)
    opener, cert, password = _opener()
    settings = LinkedDataHubSettings(cert_pem_path=cert, cert_password=password)
    for example in EXAMPLES:
        if not names or example.name in names:
            document(example, opener, settings)


if __name__ == "__main__":
    main(sys.argv[1:])
