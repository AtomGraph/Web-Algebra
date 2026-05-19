# Web Algebra spec gaps

This file tracks ambiguities and omissions in `formal-semantics.md` discovered while authoring the test suite. Tests that depend on an unresolved item are marked `pytest.skip("UNCLEAR(spec): ...")` until the spec settles the question.

Format per entry:
- **Operation / property** — what's unclear
  - Assumed for now: ...
  - Proposed spec edit: ...

---

## Operations present in the implementation but absent from the spec catalog

The spec should either add these to the catalog or the impl should drop them.

- **Concat** (`operations/string/concat.py`) — no spec entry; signature unknown.
  - Assumed for now: no test file authored.
  - Proposed spec edit: add to "String Operations" with signature `Sequence Literal → Literal` (or whatever the intended shape is).
- **ExtractOntology** (`operations/schema/extract_ontology.py`) — no spec entry; sibling `Extract*` ops are spec'd.
  - Assumed for now: no test file authored.
  - Proposed spec edit: add to "Schema Operations" with concrete input/output types.

(Re-verify the full list during implementation by `ls`-ing `src/web_algebra/operations/` and diffing names against the spec catalog at `formal-semantics.md` lines 57-287.)

## Result-type and behavior ambiguities

- **Str** (`Term → Literal`) — what datatype does the result Literal carry? `xsd:string`? simple literal (no datatype)? passthrough for an already-string Literal? SPARQL `STR()` returns a simple literal; spec should pin one.
  - Assumed for now: tests assert `isinstance(result, Literal)` and lexical-form equality only; datatype assertions are skipped.
  - Proposed spec edit: state result datatype explicitly.
- **URI** (`Term → URI`) — behavior on `Literal` whose lexical form isn't a valid URI? On a `BNode`? Spec lists `BNode` as a `Term` but says nothing about `URI(BNode)`.
  - Assumed for now: only URIRef/Literal happy paths exercised; BNode and invalid-URI cases skipped.
  - Proposed spec edit: enumerate behavior across all three Term subtypes.
- **EncodeForURI** (`Literal → Literal`) — which character set / RFC? RFC 3986 unreserved? SPARQL `ENCODE_FOR_URI`? They differ on `~`, `*`, etc.
  - Assumed for now: only the uncontroversial space-to-`%20` case is asserted.
  - Proposed spec edit: cite the RFC or SPARQL function explicitly.
- **Replace** (`Literal × Literal × Literal → Literal`) — regex pattern or literal pattern? SPARQL `REPLACE` is XQuery regex; the existing fixture uses `pattern: "%20"` which works either way.
  - Assumed for now: only patterns that are valid as both literal and regex are tested.
  - Proposed spec edit: state which.
- **STRUUID** (`() → Literal`) — UUID format? UUID4? Hyphenated? Case?
  - Assumed for now: only `isinstance(result, Literal)` and "two consecutive calls differ" are asserted.
  - Proposed spec edit: state format.
- **Substitute** (`Literal × Literal × Term → Literal`) — SPARQL variable syntax matched: `?var`, `$var`, or both? How are Term values serialized into the query (URIRef → `<...>`, Literal → `"..."` with datatype? lang tag?).
  - Assumed for now: tests skipped pending spec.
  - Proposed spec edit: define accepted variable syntax and term serialization rules.
- **Merge** (`Sequence Graph → Graph`) — duplicate triples deduplicated? RDF semantics implies set union; spec is silent.
  - Assumed for now: tests assert union behavior; deduplication test marked skip.
  - Proposed spec edit: state set vs multiset semantics.
- **Bindings** (`Result → Sequence ResultRow`) — order preservation? Empty Result → empty list?
  - Assumed for now: length only is asserted; order assertions skipped.
  - Proposed spec edit: state ordering contract.

## Error semantics

The Strict Type Checking property (`formal-semantics.md` lines 291-295) says "TypeError raised for mismatched input types" but doesn't extend to other error classes:

- Missing required argument in JSON dispatch — TypeError? KeyError? ValueError?
- Unknown `@op` — ValueError? Custom exception?
- Live-service operations on network/endpoint failure — propagate? wrap? what type?
- **Variable / Value** lookup on a missing name — error or `None`?
  - Assumed for now: tests assert `pytest.raises(Exception)` (broad) for these paths; specific exception class skipped.
  - Proposed spec edit: state exception classes.

## Sequence semantics

- **ForEach** (`Sequence α × Operation → Sequence β`) — when the inner operation returns `None` or itself a sequence, what's the output shape? Filter `None`s? Flatten? The Sequence Semantics section (lines 302-306) says "Single-item operations applied element-wise" which doesn't answer the multi-item case.
  - Assumed for now: only "input length = output length" is asserted, with inner ops that return single items.
  - Proposed spec edit: define output shape across each inner-op return shape (None, single, sequence).
- ForEach over a SPARQL `Result` — is iteration order part of the contract?
  - Assumed for now: order-sensitive assertions skipped.

## Filter

- **Filter signature typo** — `formal-semantics.md` line 99: `(Sequence α × Expression → α) + (Result × Expression → Result)`. The sequence case almost certainly should return `Sequence α`, not `α`.
  - Assumed for now: all Filter tests skipped pending correction.
  - Proposed spec edit: change `→ α` to `→ Sequence α` in the sequence case.
- **Expression type** — line 27 says `Expression = Operation + Literal + Integer`, but how each kind evaluates as a predicate is undefined.
  - Proposed spec edit: define evaluation rules per Expression variant.

## Variable system

- **Variable** (`String × Any × VariableStack → ⊥`) — `⊥` (bottom) means non-terminating in type theory; presumably means "no meaningful return". But `execute_json` on the JSON layer must return *something* — what?
  - Assumed for now: return value not asserted.
  - Proposed spec edit: state JSON-layer return value (`None`? the bound value?).
- **Variable System property** (line 311) is internally contradictory: "Sets variables in current scope, Variable operation manages the stack." Sets-in-current vs manages-the-stack are different operations.
  - Proposed spec edit: split into two sentences clarifying which operation is responsible for scope creation vs assignment.
- **Value lookup precedence** — when a name exists both in the variable stack and in the context, which wins?
  - Assumed for now: precedence-collision tests skipped.

## Context system

- **Current** (`Any → Any`) — behavior when context is unset (default `{}` per the abstract type signature)? Returns the empty dict? Errors?
  - Assumed for now: only the "context-set" happy path is tested.
- **Value** — which context container shapes are supported? Spec line 315 says context is `Any` and "varies by operation"; line 318 says Value "accesses context values and variables from stack" without enumerating shapes. The impl supports `ResultRow` (`context[name]`) and any object with `getattr(context, name)`, but not plain `dict`. The default `Operation.context: Any = {}` is a dict, which suggests dict should be valid — but the spec doesn't make that explicit.
  - Assumed for now: dict-context test skipped pending spec.
  - Proposed spec edit: enumerate the supported context container shapes for Value (ResultRow only? + dict? + arbitrary objects?).
- **Execute** (`Operation → Any`) — narrative description is missing entirely. What does Execute do that JSON dispatch doesn't already?
  - Assumed for now: all Execute tests skipped pending spec narrative.
  - Proposed spec edit: add narrative description.

## Schema operations

- **ExtractClasses / ExtractDatatypeProperties / ExtractObjectProperties** (`URI → Graph`) — what does the URI parameter denote? A SPARQL endpoint, a document URL, or an ontology IRI? Spec narrative is silent.
  - Assumed for now: only TypeError-on-non-URIRef case is exercised.
  - Proposed spec edit: name the URI's role explicitly.

## JSON dispatch surface

The `formal-semantics.md` Execution Architecture section (lines 49-55) declares `execute_json(arguments: dict, variable_stack: list) -> Any` but never specifies the keys that each operation expects in `arguments`. In practice the existing positive fixtures confirm key names for a subset of operations (Str/URI/EncodeForURI: `input`; Replace: `input`/`pattern`/`replacement`; CONSTRUCT: `query`/`endpoint`; PUT: `url`/`data`; ldh-CreateContainer: `parent`/`title`/`slug`; ldh-AddSelect: `url`/`query`/`title`; SPARQLString: `question`).

The remaining operations (ResolveURI, Merge, Substitute, Variable, Value, Bindings, ForEach, Filter, Execute, GET, POST, PATCH, SELECT, DESCRIBE, schema and most LDH ops) have unverified JSON arg shapes. Tests for those JSON layers are skipped with `UNCLEAR(spec)`.

- Assumed for now: ForEach uses `{select, operation}` (Python param `select_data` shortened to `select`) — used by `tests/fixtures/positive/for-each-sequence.json`.
- Proposed spec edit: per-operation JSON arg key documentation, or a stated rule (e.g. "JSON arg keys equal Python parameter names").

Pending fixtures (will be added once spec confirms key shapes):
- `tests/fixtures/positive/nested-resolve-uri.json` — ResolveURI keys.
- `tests/fixtures/positive/variable-and-value.json` — Variable + Value keys.
- `tests/fixtures/positive/substitute-template.json` — Substitute keys.
- `tests/fixtures/positive/merge-two-graphs.json` — Merge keys.

## Spec/impl divergences observed on first run

These four assertions were written from `formal-semantics.md` and failed against the implementation. They are not harness bugs — each is a place where the spec and code disagree, and the team needs to decide which side moves.

- **`tests/unit/test_str.py::TestStrPure::test_non_term_raises_type_error`** — Spec's Strict Type Checking property mandates TypeError on mismatched input. `Str.execute([1, 2, 3])` returns a Literal instead of raising. Either Str should validate `term` is a `URIRef | Literal | BNode`, or the spec should carve out an exception for Str ("accepts any value, casts via `str(...)`").
- **`tests/unit/test_select.py::TestSELECTPure::test_wrong_endpoint_type_raises`** — Spec: `URI × Literal → Result`. `SELECT.execute(Literal(...), Literal(...))` does not raise TypeError; it proceeds to an HTTP call. Same conflict between Strict Type Checking and the implementation, scaled to a network side effect.
- **`tests/unit/test_select.py::TestSELECTPure::test_wrong_query_type_raises`** — Same as above with `query=URIRef(...)`.

## Live-service operations

- **GET, POST, PUT, PATCH** — return types are spec'd, but content negotiation, headers, status-code handling, redirects, timeouts are all silent.
- **SELECT, CONSTRUCT, DESCRIBE** — same: behavior on 4xx/5xx, malformed query, network failure unspecified.
- **ldh-*** — most return `Any`. What is the meaningful assertion for tests against a live LDH instance?
- **SPARQLString** (`Literal → Literal`) — generates SPARQL "from natural language". Non-deterministic (LLM); no testable invariant beyond return type.
  - Assumed for now: pure-layer tests cover input-type validation only; live tests assert return types under the relevant marker.
  - Proposed spec edit: define error-handling contract for each I/O op.
