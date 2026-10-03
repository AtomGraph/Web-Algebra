# Web-Algebra Architecture Evaluation

*Scope: Web-Algebra (this repo, v1.5.0, Python/rdflib) evaluated on the conceptual and
code level, and compared against its Java/XML sibling `../REST-VKG` (webalgebra module
v1.12.0-SNAPSHOT, Jena/Saxon). Written 2026-07-12.*

## Verdict in brief

The premise — an LLM compiling a whole Linked Data workflow into a declarative,
composable operation document instead of issuing step-by-step tool calls — is sound,
and was ahead of its time. The weak points are not the idea but its contracts:
`formal-semantics.md` is a type *catalog* rather than a semantics, the two sibling
implementations have quietly forked (both in operations and in execution model), and
the Python codebase has a handful of structural debts (mutable shared state, a
god-class `Operation`, a three-way execution surface) that are cheap to fix now and
expensive later. The rdflib-based data model is the right choice and its JSON-LD
boundary discipline is genuinely well designed. Part II proposes a three-tier plan:
unify the spec, sync the operation set both ways, then pay down the Python debts.

---

# Part I — Evaluation

## 1. The premise: composed operations as LLM-emitted bytecode

**Sound? Yes.** The core bet (README: agents "compile entire workflows into optimized
JSON 'bytecode' that executes atomically") separates *planning* from *execution*:

- One LLM turn produces the whole program; execution is then deterministic, cheap, and
  free of per-step model round-trips. For N-row ForEach workloads this is the
  difference between 1 LLM call and O(N) calls.
- The artifact is inspectable and replayable — a JSON document you can review, diff,
  version, and re-run, which per-step tool calling can never give you.
- The value domain is RDF-native (`URIRef`/`Literal`/`Graph`/`Result`), so data flows
  between operations *as RDF*, not as strings squeezed through generic tool-call JSON.
  This is the part most "agent + SPARQL endpoint" designs get wrong.

**Innovative? Yes, with context.** The now-mainstream pattern of "have the model emit
a program over the tool surface instead of chaining tool calls" (CodeAct-style agents,
code-mode MCP execution) arrived after this design. Web-Algebra's distinctive
contributions beyond that pattern are:

1. **A domain algebra, not a general-purpose language.** The constrained operation set
   is what makes documents verifiable, replayable, and safe — an LLM emitting Python
   can do anything; an LLM emitting Web-Algebra can only do what the algebra permits.
2. **XSLT lineage for control flow** — `ForEach`/`Value`/`Current`/`Variable` map to
   `xsl:for-each`/`xsl:value-of`/`current()`/`xsl:variable`, a proven declarative
   iteration model rather than an invented one.
3. **JSON-LD as both code and data carrier** (§3) — the same document embeds RDF
   payloads and operations, discriminated by `@`-keys.

**Where the premise is under-delivered** (these are contract gaps, not design flaws):

- **No validation phase.** The "bytecode" is never typechecked before running. A type
  error in operation 7 surfaces after operations 1–6 have already POSTed/PUT to live
  servers; there is no dry-run, and HTTP effects are not transactional. A compiler
  metaphor implies a checker; the checker is missing.
- **Quotation is implicit.** `process_json` evaluates nested `@op` eagerly,
  depth-first — except `ForEach`, which receives its `operation` argument raw and
  evaluates it once per row (`for_each.py:53`). That makes `ForEach` a special form in
  the Lisp sense, but nothing in the spec or the schema declares which arguments are
  evaluated and which are quoted. Any future conditional/short-circuit op will hit the
  same wall.
- **Effects are typed as pure functions.** `POST : URI × Graph → Result` reads like
  arithmetic; nothing distinguishes effectful operations, their ordering guarantees
  (currently: top-level JSON array order + ForEach row order), or their failure
  behavior.

## 2. The formal definitions (`formal-semantics.md`)

**What it does well.** Every operation gets a dual signature (abstract +
concrete Python), the abstract type language is compact (`Term = URI + Literal +
BNode`, `Maybe`, `Sequence α`), and the Strict Type Checking property is stated
explicitly. As a catalog it is mostly accurate against the code.

**What it is not: a semantics.** There are no evaluation rules. The document never
defines:

- what nesting means (evaluation order, eager vs quoted arguments);
- what a top-level JSON array means (sequencing? variable-stack accumulation? —
  `operation.py:130-137` implements accumulation, the spec is silent);
- how ForEach context propagates and how `Value` resolves the name (`$var` stack vs
  context lookup is stated informally at best);
- what happens on error (class, propagation, partial results).

The type system also gives up exactly where the DSL is most interesting:
`Context = Any` (`formal-semantics.md:20`), `VariableStack = [Dict[String, Any]]`,
and the control-flow ops are typed `Any → Any`. The algebra's *data* operations are
precisely typed; its *composition* operations are untyped.

Concrete defects, all cheap to fix:

- `Variable : String × Any × VariableStack → ⊥` (`formal-semantics.md:69`) — `⊥` means
  non-termination; the intended type is `Unit`.
- Filter's sequence case reads `Sequence α × Expression → α` (`formal-semantics.md:99`)
  — should be `→ Sequence α`.
- `Concat` and `ExtractOntology` are implemented but absent from the catalog.
- `tests/SPEC_GAPS.md` tracks **30+ places where the spec underdetermines the
  implementation** — datatype of `Str` results, `Substitute`'s variable syntax and
  term-serialization rules, ForEach output shape for `None`/sequence inner results,
  the entire error-semantics column, and the JSON arg-key names for ~20 operations.
  The spec-driven test suite is the best evidence of the gap: dozens of tests are
  `pytest.skip("UNCLEAR(spec)")`.

**The deeper problem: the spec has forked.** REST-VKG carries its own
`docs/WEB-ALGEBRA.md` — 994 lines of *operational* semantics (execution model,
patterns, examples) versus this repo's 360-line type catalog. Neither references the
other; each has drifted toward its host implementation. For two projects that "should
be in sync in terms of the operations and their signatures", the single highest-value
move is one shared spec (Part II, Tier 1).

## 3. The JSON DSL

**Strengths.**

- `@op`/`args` rides JSON-LD's established `@`-keyword convention, so one document
  carries both operations and RDF data with unambiguous discrimination.
- The best design element in the codebase is the **quasi-quotation of JSON-LD
  bodies**: a dict carrying `@context`/`@graph`/`@id`/`@type` is treated as data, but
  `_resolve_jsonld` (`operation.py:144-175`) walks it and evaluates embedded `@op`
  holes in place — e.g. an `@id` computed from a runtime binding — while deliberately
  *not* parsing to a `Graph`, so the consuming operation can parse with its own base
  IRI. The reasoning is documented in the code (`operation.py:102-119`) and it is
  correct: central parsing would freeze unresolved holes into blank nodes.
- Flat, schema-describable JSON is arguably *easier* for an LLM to emit correctly than
  free-form code, and trivially validatable — once a validator exists.

**Weaknesses.**

- **Verbosity.** Every URI-valued argument needs a nested
  `{"@op": "URI", "args": {"input": ...}}` cast, every string interpolation a
  `Concat`/`Value` tree. In `examples/united-kingdom-cities.json`, a two-step workflow
  costs 104 lines and 14 operation nodes, roughly a third of which are casts and
  variable plumbing. This is a *type-system choice* (§5) — plain JSON strings become
  `xsd:string` literals (`operation.py:275-277`), so URIs must be cast explicitly —
  but the cost lands on every document and every LLM emission. Sugar is available
  without weakening the typing: `{"@id": "..."}` is already valid JSON-LD for "this is
  a URI" and could be accepted anywhere a URI is expected.
- **No envelope.** Documents have no version, no namespace, no name — just a bare
  array. The Java XML side has `xmlns="https://w3id.org/atomgraph/web-algebra"`; the
  JSON side has nothing to dispatch or validate against.
- **The JSON-LD sniff** (`_JSONLD_KEYS`, `operation.py:17`) is a heuristic: any dict
  containing `@type` is data. The code comment argues these keys are unambiguous, and
  within RDF workflows that mostly holds, but it is a global reserved-word rule the
  spec never states.
- **Arrays are overloaded**: top-level array = sequential program with shared variable
  stack; array under `ForEach.operation` = per-row sequence where only the last
  non-`None` result is kept (`for_each.py:84-97`); array elsewhere = plain argument
  list. Three meanings, zero spec lines.
- **JSON arg keys are folklore.** The spec gives Python parameter names; the JSON
  layer uses different keys (`select` vs `select_data`), confirmed only by fixtures
  (SPEC_GAPS "JSON dispatch surface").

## 4. The Python codebase

Ranked by how much they matter:

1. **Mutable default arguments** — `execute_json(self, arguments, variable_stack:
   list = [])` (`operation.py:56`), `process_json(..., context: dict = {},
   variable_stack: list = [])` (`operation.py:83-84`), and the class field
   `context: Any = {}` (`operation.py:31`). Python evaluates these once; every call
   that omits the argument shares one list/dict across the process. Today the
   single-threaded interpreter mostly masks it; the day two documents run in one
   process (the MCP server is exactly that), variables leak between executions. This
   is the one outright *bug class* in the core.
2. **`Operation` is a god class.** Registry, the whole interpreter (`process_json` +
   `_resolve_jsonld`), variable-stack management, and five type-conversion helpers all
   live in the ABC every operation inherits (`operation.py`, 345 lines). The
   interpreter is not an operation concern; it should be a separate module holding an
   execution context — which is also the precondition for parallelism (§6).
3. **The `execute()` contract is violated by its own flagship op.**
   `ForEach.execute()` raises `NotImplementedError` (`for_each.py:42-44`) because the
   pure layer has no way to run an operation with context — i.e. the algebra's central
   higher-order operation has no pure form, only a JSON form. `Bindings` and
   `ldh-List` return `list[dict]`, many `ldh-*` ops return `Any`. The abstract
   signature `execute(*args)` is variadic while every implementation is fixed-arity,
   so type checkers verify nothing.
4. **pydantic is decorative.** `extra="allow"`, no field validation, hand-written
   `inputSchema()` dicts that often omit `"type"` (`for_each.py:24-34`) and are never
   used to validate anything. The DSL's missing validator (§1) could be generated from
   real pydantic models; today neither exists.
5. **Three execution surfaces per operation** (`execute` / `execute_json` /
   `mcp_run`) is a triple maintenance burden, and it shows: `ForEach.mcp_run` returns
   the static string "ForEach operation completed" (`for_each.py:112-114`). 21 of 43
   ops are MCP-exposed; the boundary between "MCP tool" and "DSL-only" is undocumented.
6. **No exception taxonomy.** `TypeError` vs `ValueError` vs raw
   `urllib.error.HTTPError` varies by op; SPEC_GAPS' error-semantics section exists
   because callers cannot classify failures.
7. **Duplication.** Seven HTTP-backed ops repeat the same `LinkedDataClient`
   construction in `model_post_init`; isinstance-check boilerplate opens every
   `execute()`.
8. **Minor:** `_serialize_for_json_context` (`operation.py:177-188`) is dead code; no
   retry on transient network failures (only 429 `Retry-After` is honored).

**What is genuinely good** — worth saying plainly, because it should be preserved
through any refactor:

- The **JSON-LD → Graph boundary** is exactly right: `to_graph()`
  (`operation.py:215-242`) is the single parse point, each op applies its own base
  IRI, and the design rationale is written down where it matters.
- `client.py` handles 308 redirects and 429 backoff correctly, with client-cert auth
  cleanly isolated in settings.
- The registry + auto-discovery pattern is clean and scales.
- The **spec-driven test discipline** (203 tests authored from the spec alone,
  `SPEC_GAPS.md` recording every ambiguity with a proposed spec edit) is a practice
  most projects never reach. The gaps it found are the spec's problem, not the suite's.

## 5. The rdflib data model

Right choice, well executed at the boundaries. `Node`/`Graph`/`Result` as the value
domain keeps datatype and language-tag fidelity end-to-end; `JSONResult`
(`json_result.py`) is a clean adapter between rdflib results and the SPARQL JSON
wire format; `POST`/`PUT` returning a `Result` of `{status, url}` bindings is a nice
touch — HTTP responses become queryable data, and it happens to match REST-VKG's
`ResultSet` shape exactly.

Two observations:

- **Leaf typing is principled and expensive.** Every plain JSON string becomes
  `Literal(..., datatype=xsd:string)` — never a URI (`operation.py:275-277`). That
  strictness is defensible RDF hygiene (Java's `String`-typed leaves lose
  datatype/lang information, see §6) and it is what forces the `URI` cast operation
  and much of the DSL's verbosity. Keep the typing; add sugar at the JSON boundary.
- The stated convention "execute() is pure rdflib" holds for the data-plane ops but
  not the control plane (§4.3). Either the convention gets a carve-out for
  interpreter-level forms (ForEach, Execute, Variable, Value, Current, Filter,
  Bindings) — which is honest, they are special forms, not term functions — or those
  need pure formulations. The spec should say which.

## 6. Python ↔ Java: parity and divergence

### Operation parity (registry names)

| | Operations |
|---|---|
| **Shared core (20)** | GET, POST, PUT, SELECT, DESCRIBE, CONSTRUCT, Merge, ForEach, Value, Str, Concat, Replace, EncodeForURI, ResolveURI, Substitute, Variable, Current, Execute, STRUUID/StrUUID, SPARQLString |
| **Java-only (1)** | Iterate — stateful pagination: `param` initialization, `next-iteration` passing, `break` conditions (`IterateOperation.java`, 244 lines) |
| **Python-only, generic (9)** | PATCH, Values, URI, Filter, Bindings, ExtractClasses, ExtractDatatypeProperties, ExtractObjectProperties, ExtractOntology |
| **Python-only, product-specific (14)** | the `ldh-*` LinkedDataHub operations |

(Java's GRDDL is superseded by the client-side response filter and excluded.)

### Three deep divergences — and per-op verdicts

**a. ForEach: map → List (Python) vs parallel map-merge → Model (Java).**
Python's ForEach returns the list of per-row results (`for_each.py:79-110`); Java's
requires the select to yield a `ResultSet`, requires the inner operation to return a
`Model`, executes rows via `parallelStream()`, and merges into one `Model`
(`ForEachOperation.java:61-100`). **Verdict: Python's shape is the better algebra;
Java's execution model is the better runtime.** `Sequence α × (α → β) → Sequence β`
is more general — Java's fused map-merge cannot express "PUT each row's document and
give me the statuses" (the UK-cities example) without contortion, and its two
`instanceof` gates are exactly the kind of restriction a spec should not bake in.
Java's merge is `Merge(ForEach(...))` — an explicit composition Python already has.
Conversely, Java's per-row **immutable context clone enabling parallel iteration** is
strictly better than Python's shared mutable stack. Sync direction: spec ForEach as
sequence-returning with the map-merge documented as a fused specialization Java may
keep; Python adopts context isolation (and then parallelism) from Java.

**b. Variables/context: mutable stack (Python) vs immutable `ExecutionContext`
(Java).** Java's context is a persistent structure — `withVariable`/`withBinding`
return new instances (`ExecutionContext.java:81-98`), with a progress emitter riding
along (`start:`/`complete:`/`error:` events). **Verdict: Java wins outright.** This is
thread safety, ForEach-row isolation, and observability in one move, and it is the
enabler for fixing Python issues §4.1 and §4.2 in a way that converges the two
codebases instead of diverging them further.

**c. Leaf typing: RDF terms (Python) vs Strings (Java).** Java string ops return
`String` and `Value` stringifies RDF nodes; Python returns typed `Literal`s and keeps
`URIRef`/`Literal` distinct end-to-end. **Verdict: Python wins.** A `String`-typed
data plane silently drops datatypes and language tags — the exact failure RDF systems
exist to avoid. Long-term, Java should move its operation returns toward
`RDFNode`-typed values; the shared spec should define signatures in abstract RDF terms
(as `formal-semantics.md` already does) either way.

### Maturity gaps (Java ahead, no controversy)

- **Iterate** — no Python equivalent for paginated APIs; the biggest functional gap.
- **Parallel ForEach** — blocked in Python only by the mutable context.
- **Progress events** — Python has `logging.info` only; no structured lifecycle.
- **SPARQLString hardening** — Java takes question + endpoint, injects the service's
  AGENTS.md plus date/timezone into the prompt, and retries 3× with exponential
  backoff; Python takes a bare question with no retries.
- **Hybrid SELECT** — Java's SELECT accepts a remote endpoint *or* a local graph;
  Python is endpoint-only, which blocks querying intermediate in-memory results.
- Deployment/observability (Docker, health endpoints, timing metrics) — product-level
  rather than algebra-level, but worth noting.

---

# Part II — Implementation plan

Three tiers, independently executable, in value order. Decisions already made:
divergences are resolved per-op as recommended above; parity scope is the generic
core in both directions (`ldh-*` stays Python-only, declared as a product extension);
all three tiers are in scope.

## Tier 1 — One spec, made whole (highest value, zero code risk)

1. **Unify the fork.** Merge this repo's `formal-semantics.md` (type catalog) and
   REST-VKG's `docs/WEB-ALGEBRA.md` (operational semantics) into a single canonical
   spec shared by both repos (one home, the other references it — natural candidate:
   a spec file under the `w3id.org/atomgraph/web-algebra` namespace both already
   implicitly claim). Structure: type system → **evaluation rules** → operation
   catalog → error semantics → serializations (JSON and XML as two concrete syntaxes
   of one abstract syntax).
2. **Write the missing evaluation rules** (the §2 list): eager depth-first argument
   evaluation; *quoted operands declared per-op* (ForEach.operation, Execute's body);
   top-level array sequencing incl. variable-stack accumulation; ForEach context
   propagation and `Value` resolution order (`$var` stack lookup vs context binding);
   the three meanings of arrays; effect annotation for GET/POST/PUT/PATCH/SELECT/
   CONSTRUCT/DESCRIBE and their ordering guarantees.
3. **Resolve `tests/SPEC_GAPS.md` item by item** — it already contains proposed edits
   for nearly every entry; most are one-line decisions (Str result datatype,
   EncodeForURI's RFC, Merge set-semantics, Bindings ordering, error classes,
   JSON arg-key table). Fix the two catalog defects (`⊥` → `Unit`,
   Filter → `Sequence α`) and add the two missing entries (Concat, ExtractOntology).
4. **Declare the extension model**: `ldh-*` as a named product-specific extension
   namespace; Iterate added to the core catalog (from Java).

*Verification:* every resolved item un-skips its `UNCLEAR(spec)` tests;
`uv run pytest -m 'not network and not sparql and not ldh'` green with strictly fewer
skips than today.

## Tier 2 — Operation & signature sync (generic core, both directions)

**Python gains:**

| Item | Notes |
|---|---|
| `Iterate` | Port from `IterateOperation.java` (params, next-iteration, break condition). Spec first (Tier 1), then implement + spec-driven tests. |
| Hybrid `SELECT` | Accept a `Graph` argument alternative to `endpoint` (query local/intermediate results via rdflib). Mirrors `SelectOperation.java`. |
| `SPARQLString` parity | Add endpoint parameter and context injection; add bounded retry with backoff. |
| Parallel ForEach | After Tier 3.2 (immutable context). Row isolation semantics per unified spec. |

**Java gains** (tracked here, implemented in REST-VKG): `PATCH`, `Values`, `Filter`,
`Bindings`, `URI`, and the four `Extract*` schema ops — signatures taken verbatim from
the unified catalog.

**Harmonizations:**

- ForEach per verdict §6a: spec is sequence-returning; Java either generalizes or its
  map-merge is documented as a fused `Merge ∘ ForEach` specialization.
- Registry-name alignment: `STRUUID` vs `StrUUID` — recommend `STRUUID` (matches the
  SPARQL function name, which is the naming rule the other ops already follow).
- POST/PUT `{status, url}` result shape: already aligned; codify it in the catalog.

*Verification:* a parity table in the unified spec, asserted by a test in each repo
that diffs its registry against the spec catalog (Python: registry names vs a
committed list; the SPEC_GAPS re-verify note at `tests/SPEC_GAPS.md:23` already asks
for exactly this).

## Tier 3 — Python code health

Ordered so each step stands alone:

1. **Kill mutable defaults.** `variable_stack: list = None` → `if None: []` (or
   required-arg) in `execute_json`/`process_json`/all ops; `context` field default via
   pydantic `default_factory`. Mechanical, high value. (`operation.py:31,56,83-84`
   and every operation's `execute_json`.)
2. **Extract the interpreter.** Move `process_json`, `_resolve_jsonld`, and
   variable-stack handling out of `Operation` into an `interpreter.py` with an
   immutable `ExecutionContext` (variables + current binding + progress callback) —
   deliberately the same shape as `ExecutionContext.java`, converging the two
   codebases. Operations keep `execute`/`execute_json`; `self.context` and the stack
   parameter are replaced by the context object.
3. **Exception taxonomy.** `WebAlgebraError` base; `UnknownOperationError`,
   `OperationTypeError`, `VariableNotFoundError`, `HttpOperationError(status, url)`.
   Raise-sites updated; spec's error-semantics section (Tier 1.2) is the contract.
4. **Deduplicate the HTTP plumbing.** One client factory/mixin for the 7 ops that
   construct `LinkedDataClient` in `model_post_init`; add transient-failure retry at
   the client, not per-op.
5. **Honest contracts.** Delete `_serialize_for_json_context`; declare the
   interpreter-level special forms (ForEach, Execute, Variable, Value, Current) as
   such instead of pretending at a pure `execute()` (drop the `NotImplementedError`
   stub per the unified spec); give ForEach a real `mcp_run` or remove its `MCPTool`
   claim; replace hand-written `inputSchema()` dicts with schemas generated from
   pydantic argument models — which also yields the missing pre-execution document
   validator (§1) nearly for free.

*Verification:* full suite `uv run pytest` after each step; step 2 additionally
verified by the integration fixtures in `tests/integration/` (behavior-preserving
refactor); step 5's validator gets new negative fixtures (malformed documents rejected
before any HTTP effect).

## Suggested sequencing

Tier 1 first (it unblocks skipped tests and is the sync keystone). Tier 3.1 anytime
(it is a bug fix). Tier 3.2 before the parallel-ForEach item of Tier 2. Everything
else is independent.
