"""Checks a JSON plan against the operations' schemas and formal-semantics.md,
without running it: shared by the operation guide's test and the examples'.

- every operation exists, its argument names are in its inputSchema() and
  its required ones are present;
- an argument the spec types `URI` (its `JSON:` lines, the Appendix A table)
  is not a plain JSON string, which is always a literal.

It walks the whole plan, so it reaches ForEach and Iterate bodies that an
offline run never executes.
"""

from __future__ import annotations

import re
from pathlib import Path

from web_algebra.operation import Operation

SPEC = (Path(__file__).resolve().parent.parent / "formal-semantics.md").read_text()


def _spec_entries() -> dict:
    """name → {"abstract": result type, "uri_args": {...}} from the catalog's
    code blocks and the Appendix A table."""
    entries = {}
    for m in re.finditer(r"^\*\*([A-Za-z][\w]*)\*\*[^\n]*\n(?:[^\n]*\n)*?```\n(.*?)```", SPEC, re.M | re.S):
        name, block = m.group(1), m.group(2)
        abstract = re.search(r"Abstract:(.*?)(?=\n\S|\Z)", block, re.S)
        json_line = re.search(r"JSON:(.*?)(?=\n\S|\Z)", block, re.S)
        entries.setdefault(
            name,
            {
                "abstract": " ".join(abstract.group(1).split()).rsplit("→", 1)[1].strip() if abstract else None,
                "uri_args": _uri_args(json_line.group(1)) if json_line else set(),
            },
        )
    # §4.6: the four extractions share one block
    for name in ("ExtractClasses", "ExtractDatatypeProperties", "ExtractObjectProperties", "ExtractOntology"):
        entries[name] = {"abstract": "Graph", "uri_args": {"endpoint"}}
    # Appendix A table
    for m in re.finditer(r"^\| `(ldh-[\w]+)`[^|]*\| `(.*?)`", SPEC, re.M):
        name = m.group(1)
        entries[name] = {
            "abstract": "Result" if not name.startswith("ldh-Generate") else None,
            "uri_args": _uri_args(m.group(2)),
        }
    return entries


def _uri_args(text: str) -> set:
    """Argument names typed exactly `URI` (not `URI + Literal`)."""
    return {
        name
        for name, rest in re.findall(r"(\w+): URI\b(.{0,3})", text)
        if not rest.strip().startswith("+")
    }


SPEC_ENTRIES = _spec_entries()


def check_static(node, problems, path="$"):
    if isinstance(node, list):
        for i, item in enumerate(node):
            check_static(item, problems, f"{path}[{i}]")
        return
    if not isinstance(node, dict):
        return
    if "@op" in node:
        name = node["@op"]
        if name not in Operation.registry:
            problems.append(f"{path}: unknown operation {name}")
            return
        schema = Operation.registry[name].inputSchema()
        args = node.get("args", {})
        properties = set(schema.get("properties", {}))
        for key in args:
            if key not in properties:
                problems.append(f"{path}: {name} has no argument {key!r}")
        for key in schema.get("required", []):
            if key not in args:
                problems.append(f"{path}: {name} misses required {key!r}")
        for key in SPEC_ENTRIES.get(name, {}).get("uri_args", set()):
            if isinstance(args.get(key), str):
                problems.append(f"{path}: {name}.{key} is a plain string; a URI is {{\"@id\": ...}}")
        for key, value in args.items():
            check_static(value, problems, f"{path}.{name}.{key}")
        return
    for key, value in node.items():
        check_static(value, problems, f"{path}.{key}")
