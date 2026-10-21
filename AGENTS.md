# AGENTS.md

Guidance for coding agents (and people) working on this repository.

## What this is

Web Algebra is a composable algebra of RDF operations — loading, querying,
transforming and writing Linked Data — written as a JSON DSL. A plan is a tree
of operations that a model can generate from a natural-language instruction
and the interpreter evaluates. It runs as a CLI (`web-algebra`) and as an MCP
server (`web-algebra-mcp`, stdio; `web_algebra.server:app`, streamable HTTP).

`formal-semantics.md` is the normative specification: its evaluation model is
XPath/XSLT's, applied to RDF (flat sequences, the empty sequence as Unit, a
focus of Current/Position/Last, typed errors), and §4 is the operation
catalogue. Appendix A covers the LinkedDataHub (`ldh-`) operations.

## Commands

```bash
uv sync --group dev                     # install, with pytest and ruff
uv run ruff check                       # lint, as CI runs it
uv run pytest                           # the offline suite, as CI runs it
uv run pytest -m ldh                    # against a LinkedDataHub (see below)
uv run web-algebra --from-json examples/city-profiles/plan.json
uv run web-algebra-mcp                  # MCP server, stdio
uv run uvicorn web_algebra.server:app --reload   # MCP server, streamable HTTP
```

CI runs `ruff check` and `pytest` on Python 3.10 to 3.14, from the locked
environment (`uv sync --locked`: change `pyproject.toml`, then `uv lock`).

A `v*` tag publishes to PyPI and makes a GitHub Release from the version's
section of `CHANGELOG.md` (`.github/workflows/release.yml`). It cannot be
undone, so never push a tag without being asked. A release bumps the version
in `pyproject.toml` and `server.json` (the MCP Registry entry) together;
`tests/test_packaging.py` checks they agree.

### Certificates and secrets

The CLI, the MCP server and the tests read the LinkedDataHub client
certificate from `CERT_PEM_PATH` and its password from `CERT_PASSWORD`
(the CLI's `--cert_pem_path` / `--cert_password` override them). Read the
password from a file rather than typing it:

```bash
export CERT_PEM_PATH=../LinkedDataHub/ssl/owner/cert.pem
export CERT_PASSWORD="$(cat ../LinkedDataHub/secrets/owner_cert_password.txt)"
```

Never write a password, key or token into a tracked file, a command shown in
docs, or a commit — use the variables.

### Test markers

`pyproject.toml` deselects `network`, `sparql` and `ldh` by default:

- `ldh` — needs a LinkedDataHub v6 instance and the certificate variables.
  The examples run against `https://localhost:4443/` (`LDH_BASE` selects
  another) and remove what they wrote unless `WA_KEEP_EXAMPLES=1`.
- `network`, `sparql` — need live HTTP or SPARQL endpoints.
- `unit` and `integration` are applied automatically to `tests/unit/` and
  `tests/integration/`.

## Layout

```
src/web_algebra/
  operation.py          Operation base class, registry, process_json, to_graph
  mcp_tool.py           MCPTool mixin (mcp_run)
  main.py               CLI; list_operation_subclasses discovers operations
  server.py, __main__.py  MCP servers (HTTP, stdio)
  client.py             HTTP clients: conditional writes, redirects
  sparql_restrict.py    binding restriction (Substitute, Values)
  rfc3986.py            reference resolution
  prompts/system.md     the operation guide given to the model
  operations/           the operations, one class per module
    linked_data/ sparql/ string/ schema/ linkeddatahub/
formal-semantics.md     the specification
examples/               worked plans, each with its instruction and checks
tests/
  unit/                 spec-derived tests, one area per file
  integration/ fixtures/  positive/negative JSON fixtures
  test_system_prompt.py the operation guide checked against the code and spec
  test_examples.py      examples checked offline, run with -m ldh
  plan_check.py         static plan checker shared by both
scripts/document_examples.py  regenerates examples/*/README.md from a live run
```

## Architecture

- **Operations** subclass `Operation` (and `MCPTool` to be exposed over MCP)
  and implement `description()`, `inputSchema()`, `execute()`,
  `execute_json()` and `mcp_run()`. The name is the class name; `ldh-`
  operations override `name()`.
- **Registration**: `list_operation_subclasses()` walks
  `web_algebra.operations` and the CLI, the MCP server and the test harness
  each register what it finds. Putting a module under `operations/` is all it
  takes.
- **The DSL**: `{"@op": "Name", "args": {...}}`, nested freely;
  `Operation.process_json()` evaluates a plan recursively. `ForEach` sets the
  focus that `Current`, `Position` and `Last` read; `Variable` binds a name in
  the current scope and `Value` reads it, or a column of the focus row.
  `formal-semantics.md` §2 defines the document forms.

### RDF type convention

The system works in the rdflib type system (`Node`, `Result`, `Graph`); JSON is
only the transport, converted at fixed boundaries:

- **`execute()` is pure rdflib** — it takes and returns `Node` / `Result` /
  `Graph` only. Never accept a `dict` here.
- **`execute_json()` is the JSON boundary** — it resolves its arguments with
  `Operation.process_json()` and converts any JSON-LD body to a `Graph` with
  **`Operation.to_graph()`** before calling `execute()`. `to_graph` is the
  single place JSON-LD is parsed and the only place an operation applies its
  base IRI (`to_graph(data, base=<target url>)`). An input that is already a
  `Graph` passes through unchanged.
- **`process_json()` never parses JSON-LD to a `Graph`** — it resolves
  `@op`/variables in place and returns plain data. It can't know an
  operation's base IRI, and eager parsing would freeze unresolved `@op` holes
  (an op-valued `@id` would silently become a blank node).
- **`mcp_run()`** takes plain MCP arguments and returns MCP content.

## Rules

- **The spec leads.** A change in behaviour is a change to
  `formal-semantics.md` first, then the code, in the same PR.
- **Standards are not negotiable.** An operation defined by a W3C
  counterpart (SPARQL 1.1, XPath functions, RFC 3986, the Graph Store
  Protocol) behaves exactly like it. A divergence is a bug to fix, never a
  limitation to document. Where rdflib itself diverges, work around it in the
  generated text (see `sparql_restrict.py`) and report it upstream.
- **Tests come from the spec.** Test bodies in `tests/unit/` are derived from
  `formal-semantics.md`, not from the implementation; `tests/conftest.py` is
  harness and may use code knowledge. Write the whole set of tests for a change
  before running any. Spec ambiguities go in `tests/SPEC_GAPS.md`.
- **The operation guide is tested.** Every registered operation needs exactly
  one `## Name(args) → Result` section in `src/web_algebra/prompts/system.md` whose arguments
  match its `inputSchema()`; its examples are checked and run.
- **Examples stay runnable.** `uv run pytest tests/test_examples.py` checks
  them offline; run them with `-m ldh` after changing anything they use, and
  regenerate their READMEs with `scripts/document_examples.py`.
- **Verify the code, not its description.** Comments, docs and this file are
  claims; trace or run the code before relying on one.
- **Changes are recorded** in `CHANGELOG.md`, in the next version's section,
  `## [x.y.z] - Unreleased`; the first change after a release adds it.

## The Java implementation

`AtomGraph/REST-VKG` implements the same algebra in Java, with an XML syntax,
on Jena. The two are kept to the same specification: a semantic change here
should be checked against, and usually made in, that one too.
