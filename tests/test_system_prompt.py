"""prompts/system.md - the operation guide the model is given - says what the
operations are and do, so it is checked against the two things that define
them: each operation's inputSchema() and formal-semantics.md.

- Every registered operation has exactly one `## Name(args) → Result` section,
  and no section names an operation that does not exist.
- A heading lists exactly the schema's arguments, `name?` for an optional one
  and `a: T | b: T` for exactly-one-of alternatives.
- A heading's result type is the spec's (the `Abstract:` line, after `→`).
- Every example is checked statically - each operation exists, its argument
  names are in its schema and its required ones present, and an argument the
  spec types `URI` is not given as a plain JSON string (a string is always a
  literal) - including inside ForEach bodies an offline run would not reach.
- Every example runs offline against an HTTP stub, except those that need a
  model (SPARQLString) or a local file (ldh-AddFile).
- Where an example of a pure operation is followed by a `Result` block, the
  operation produces exactly that.

This is a test of the document against the code and the spec, not a test of
the language, so it sits outside tests/unit/.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import XSD

from tests.http_stub import StubResponse, default_handler
from web_algebra.operation import Operation

ROOT = Path(__file__).resolve().parent.parent
GUIDE = (ROOT / "prompts" / "system.md").read_text()
SPEC = (ROOT / "formal-semantics.md").read_text()

HEADING = re.compile(r"^## (?:`)?([A-Za-z][\w-]*)(?:`)?\((.*)\) → (.+)$", re.M)


# --- the guide


def _sections() -> dict:
    """name → (args text, result type, body) for every operation section."""
    found = {}
    matches = list(HEADING.finditer(GUIDE))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(GUIDE)
        name = m.group(1)
        assert name not in found, f"{name} has more than one section"
        found[name] = (m.group(2), m.group(3).strip(), GUIDE[m.end() : end])
    return found


SECTIONS = _sections()


def _json_blocks(text: str):
    """(label, parsed) for every ```json block, label being the nearest
    preceding Markdown heading."""
    blocks = []
    for m in re.finditer(r"```json\n(.*?)```", text, re.S):
        label = re.findall(r"^#+ (.+)$", text[: m.start()], re.M)
        blocks.append((label[-1].strip() if label else "", json.loads(m.group(1))))
    return blocks


def _examples():
    """Every example in the guide: (id, plan, expected result or None)."""
    out = []
    for name, (_, _, body) in SECTIONS.items():
        blocks = _json_blocks(body)
        for i, (label, plan) in enumerate(blocks):
            if label.lower().startswith("result"):
                continue
            expected = None
            if i + 1 < len(blocks) and blocks[i + 1][0].lower().startswith("result"):
                expected = blocks[i + 1][1]
            out.append((f"{name}#{i}", plan, expected))
    for i, (label, plan) in enumerate(_json_blocks(GUIDE[: GUIDE.index("# Operations")])):
        out.append((f"overview#{i}", plan, None))
    return out


EXAMPLES = _examples()


# --- the spec


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


# --- heading ↔ schema ↔ spec


def _registered() -> set:
    return set(Operation.registry)


def test_every_operation_has_one_section():
    assert set(SECTIONS) == _registered()


def _heading_args(args_text: str):
    """[(alternatives: [(name, optional)])] from `a: T, b?: T, c: T | d: T`."""
    groups = []
    for item in [s.strip() for s in args_text.split(",") if s.strip()]:
        alternatives = []
        for alt in item.split(" | "):
            name = alt.split(":")[0].strip()
            alternatives.append((name.rstrip("?"), name.endswith("?")))
        groups.append(alternatives)
    return groups


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_heading_lists_the_schema_arguments(name):
    schema = Operation.registry[name].inputSchema()
    properties = set(schema.get("properties", {}))
    required = set(schema.get("required", []))
    one_of = [tuple(b.get("required", [])) for b in schema.get("oneOf", [])]

    groups = _heading_args(SECTIONS[name][0])
    assert {n for g in groups for n, _ in g} == properties
    for group in groups:
        if len(group) > 1:
            assert sorted((n,) for n, _ in group) == sorted(one_of), f"{name}: alternatives"
        else:
            [(arg, optional)] = group
            assert optional == (arg not in required), f"{name}: {arg} optional={optional}"


@pytest.mark.parametrize("name", sorted(n for n in SECTIONS if SPEC_ENTRIES.get(n, {}).get("abstract")))
def test_heading_result_is_the_specs(name):
    assert SECTIONS[name][1] == SPEC_ENTRIES[name]["abstract"]


# --- examples, statically


def _check_static(node, problems, path="$"):
    if isinstance(node, list):
        for i, item in enumerate(node):
            _check_static(item, problems, f"{path}[{i}]")
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
            _check_static(value, problems, f"{path}.{name}.{key}")
        return
    for key, value in node.items():
        _check_static(value, problems, f"{path}.{key}")


@pytest.mark.parametrize("example_id, plan, expected", EXAMPLES, ids=[e[0] for e in EXAMPLES])
def test_example_is_well_formed(example_id, plan, expected):
    problems = []
    _check_static(plan, problems)
    assert problems == []


# --- examples, run


NEEDS_MODEL_OR_FILE = ("SPARQLString", "ldh-AddFile")


def _uses(plan, names) -> bool:
    text = json.dumps(plan)
    return any(f'"@op": "{n}"' in text for n in names)


def _render(value):
    """A result as the guide writes it: a URI as {"@id"}, a simple or
    xsd:string literal as a string, another literal as a JSON-LD value object,
    a sequence as an array."""
    if isinstance(value, list):
        return [_render(v) for v in value]
    if isinstance(value, URIRef):
        return {"@id": str(value)}
    if isinstance(value, Literal):
        if value.language:
            return {"@value": str(value), "@language": value.language}
        if value.datatype in (None, XSD.string):
            return str(value)
        return {"@value": str(value), "@type": str(value.datatype)}
    if isinstance(value, BNode):
        return {"@id": f"_:{value}"}
    return value


def _offline(request):
    if request.get_method() in ("POST", "PUT", "PATCH", "DELETE"):
        return StubResponse(200)
    return default_handler(request)


RUNNABLE = [e for e in EXAMPLES if not _uses(e[1], NEEDS_MODEL_OR_FILE)]


@pytest.mark.parametrize("example_id, plan, expected", RUNNABLE, ids=[e[0] for e in RUNNABLE])
def test_example_runs(example_id, plan, expected, settings, http_stub):
    http_stub.handler = _offline
    result = Operation.process_json(settings, plan)
    if expected is not None:
        assert _render(result) == expected
