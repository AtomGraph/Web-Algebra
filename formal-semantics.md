# Web Algebra Formal Semantics

This document is the normative specification of Web Algebra: its type system, its
JSON serialization, its evaluation semantics, and the catalog of core operations.
The Python implementation in this repository and the test suite under `tests/`
conform to it; where the two disagree, this document wins and the code is wrong.

The LinkedDataHub-specific `ldh-*` operations are a product extension and are
described in the informative Appendix A. A sibling implementation (REST-VKG,
Java) serializes the same algebra as XML under the namespace
`https://w3id.org/atomgraph/web-algebra`; this document specifies the abstract
algebra and its JSON serialization.

## 1. Type System

### 1.1 Abstract types

```
URI         = URI reference
Literal     = literal value with optional datatype IRI or language tag
BNode       = blank node
Term        = URI + Literal + BNode
Graph       = RDF graph (set of triples)
Result      = SPARQL SELECT result: a variable list and an ordered sequence
              of Bindings
Binding     = one solution row: a partial mapping from variable names to Terms
Sequence α  = ordered list of values of type α
Position    = integer ≥ 1 (XSLT-style 1-based index)
Unit        = no meaningful value (an operation executed for its effect)
Context     = the current iteration item (see §3.5); one of
              Binding + Term + Graph + JSON value
Environment = stack of variable scopes; each scope maps names to values
Operation   = an unevaluated operation form (see quoting, §3.3)
```

### 1.2 Concrete Python types

```python
URI         = rdflib.URIRef
Literal     = rdflib.Literal
BNode       = rdflib.BNode
Term        = Union[rdflib.URIRef, rdflib.Literal, rdflib.BNode]
Graph       = rdflib.Graph
Result      = rdflib.query.Result          # typically web_algebra.json_result.JSONResult
Binding     = rdflib.query.ResultRow       # or Dict[str, Term] via Bindings
Sequence    = list
Unit        = None
Environment = list[dict[str, Any]]         # the "variable stack"
```

## 2. Document Model (JSON serialization)

### 2.1 Documents

A Web Algebra document is a JSON document in one of three shapes:

1. **A single form** — most commonly an operation call object.
2. **A program** — a JSON array of forms, evaluated in order (§3.2, *sequence
   form*).
3. **An envelope** — a JSON object whose `@web-algebra` member identifies the
   dialect version and whose `program` member holds a form or program:

```json
{
  "@web-algebra": "1",
  "name": "united-kingdom-cities",
  "description": "Create a container and load UK city data into it",
  "program": [ ... ]
}
```

The envelope is optional; the bare forms remain valid. `@web-algebra` is the
version of this specification the document targets (currently `"1"`). `name`
and `description` are optional and informative. Consumers ignore unknown
envelope members (forward compatibility). An envelope without a `program`
member is invalid (`ValueError`). The envelope is recognized at the document
top level only; it is not a form and cannot be nested.

### 2.2 Forms

Every JSON value in (the program of) a document is a **form**. The kind of a
form is decided *syntactically*, by the first matching rule:

| # | Syntax | Form kind |
|---|--------|-----------|
| 1 | object with an `@op` member | **operation call** |
| 2 | object whose only member is `@id` | **URI reference** |
| 3 | object with any of `@context`, `@graph`, `@id`, `@type` | **RDF data** (JSON-LD) |
| 4 | any other object | **generic object** |
| 5 | array | **sequence** |
| 6 | string, number, boolean | **scalar** |
| 7 | null | invalid (`TypeError`) |

**Operation call.** `{"@op": Name, "args": {key: form, ...}}`. `Name` must be a
registered operation name (§4, Appendix A); otherwise the document is invalid
(`ValueError`). `args` may be omitted when the operation takes no arguments.
Argument keys are operation-specific and normative (§4); a missing required
argument raises `KeyError`.

**URI reference.** `{"@id": form}` — an object with *exactly one* member named
`@id` — evaluates to a `URI`. The inner form may be a string or any form that
evaluates to a Term; the URI is its lexical form. This is deliberately the
JSON-LD node-reference syntax: a bare node reference carries no triples, so
reusing it as the URI form is unambiguous. It replaces the verbose
`{"@op": "URI", "args": {"input": ...}}` cast in the common case:

```json
{"@op": "GET", "args": {"url": {"@id": "https://dbpedia.org/resource/London"}}}
```

Inside an *RDF data* form, `@id` keeps its JSON-LD meaning and is **not**
subject to this rule (rule 3 wins because the discrimination happens on the
enclosing document, whose other members mark it as data).

**RDF data.** An object carrying any of the four reserved JSON-LD keys
`@context`, `@graph`, `@id`, `@type` is RDF data (a JSON-LD document or
fragment), not a structure to evaluate. These are JSON-LD reserved terms with
no meaning in non-RDF JSON; this list is normative and closed. Within an RDF
data form, embedded operation-call objects ("holes", e.g. an `@id` computed at
runtime) are evaluated in place and replaced by their results; every other
value is left untouched, and the form as a whole remains a JSON structure. It
is parsed into a `Graph` only by the consuming operation, which supplies the
correct base IRI (§2.3).

**Generic object.** Evaluated member-wise: each value is evaluated as a form,
keys are preserved. This is how, e.g., SPARQL JSON term objects (§2.4) with
computed values are written.

**Sequence.** Evaluated element-wise, in order, in a fresh variable scope
(§3.4). The value is the Sequence of element values. At document top level
this is the *program* shape.

**Scalar.** Coerced to a Term:

| JSON | Term |
|------|------|
| string | `Literal` with datatype `xsd:string` |
| integer | `Literal` with datatype `xsd:integer` |
| number with fraction | `Literal` with datatype `xsd:double` |
| boolean | `Literal` with datatype `xsd:boolean` |

A plain string is *always* a string literal, never a URI; URIs are written
with the URI reference form or produced by `URI`/`ResolveURI`. `null` is not a
valid form.

### 2.3 Base IRI

RDF data forms may contain relative IRIs. The consuming operation — the one
that turns the JSON-LD into a `Graph` — resolves them against its *target*
URI (e.g. `PUT`'s `url`), by parsing with that URI as base. There is no
document-global base IRI. Fragment references like `#service` therefore
resolve against the document being written, which is the intended semantics.

### 2.4 SPARQL JSON term form

Where an operation expects a Term argument (noted in its catalog entry), the
SPARQL 1.1 Query Results JSON term object is accepted:

```json
{"type": "uri" | "literal" | "bnode", "value": "...",
 "datatype": "...IRI...", "xml:lang": "..."}
```

`datatype` and `xml:lang` are optional and only meaningful for `literal`. An
unknown `type` raises `ValueError`. This is a generic-object form whose
member values may themselves be computed by nested operation calls.

## 3. Evaluation Semantics

### 3.1 Values

Evaluation maps forms to values in the domain

```
Value = Term + Graph + Result + Sequence Value + Binding + Unit + JSON
```

(`JSON` covers RDF data forms and generic objects, which evaluate to JSON
structures with their holes filled; they become `Graph`s only at operation
boundaries.)

### 3.2 Evaluation rules

Evaluation is **eager and depth-first**: when an operation call is evaluated,
its argument forms are evaluated first, in document order, and the operation
is then applied to the resulting values. The exceptions are **quoted
operands** (§3.3).

- *Operation call*: evaluate non-quoted arguments (document order), apply the
  operation, yield its result.
- *URI reference*: evaluate the inner form; yield `URIRef` of its lexical
  form.
- *RDF data*: walk the structure; evaluate embedded operation calls in place;
  yield the resulting JSON structure.
- *Generic object*: evaluate each member value; yield the object.
- *Sequence*: push a fresh variable scope; evaluate elements in order; pop the
  scope; yield the Sequence of element values. Elements are evaluated for both
  value and effect — an element that is an effectful operation call (§3.6)
  executes even if its value is never consumed.
- *Scalar*: yield the coerced Term (§2.2).

### 3.3 Quoted operands

Some operations receive an *unevaluated* form — they are special forms in the
Lisp sense, and their quoted operands are evaluated under a different regime
(later, repeatedly, or in a different context). Quoted operands are marked
**quoted** in the catalog. They are exactly:

| Operation | Operand | Evaluation regime |
|-----------|---------|-------------------|
| `ForEach` | `operation` | once per iteration item, with that item as context |
| `Execute` | `operation` | once, in the current context and environment |

All other arguments of all operations are eagerly evaluated. An operation not
in this table never sees an unevaluated form.

### 3.4 Variable environment

The environment is a stack of scopes.

- **Binding**: `Variable` binds a name to a value in the *current* (innermost)
  scope, creating one if the stack is empty. Rebinding a name in the same
  scope overwrites it.
- **Lookup**: `Value` with a `$`-prefixed name searches scopes innermost to
  outermost; a miss raises `ValueError`.
- **Scope creation**: a fresh scope is pushed for the duration of
  (a) every sequence form, and (b) every `ForEach` iteration. Consequently a
  variable bound in a program step is visible to *subsequent* steps of the
  same program and to forms nested within them, and ceases to exist after the
  sequence ends; a variable bound inside a `ForEach` iteration does not leak
  into the next iteration.

The `$` sigil belongs to the reference syntax of `Value`, not to the variable
name: `Variable` binds `name`, `Value` reads `$name`. Because the sigil
decides the lookup domain, variable and context lookups never shadow each
other.

### 3.5 Context

The context is the current iteration item. It is established *only* by
`ForEach`, which evaluates its quoted `operation` once per item with that item
as context; nested `ForEach` shadows the outer context for the extent of its
own operand. Outside any iteration there is no context, and operations that
require one (`Current`, context-lookup `Value`) raise `ValueError`.

- `Current` yields the context item itself.
- `Value` with an unprefixed name looks the name up *in* the context item:
  - `Binding` (SPARQL row): the term bound to that variable name;
  - mapping (e.g. a JSON object item): the member value;
  - any other object: the attribute of that name;
  - a miss, or an item supporting none of these, raises `ValueError`.

### 3.6 Effects and ordering

Operations are marked in the catalog as **pure** (no observable effect),
**query** (reads external state: HTTP GET, SPARQL query), or **update**
(writes external state: HTTP POST/PUT/PATCH). `SPARQLString` calls an external
LLM service and is additionally **non-deterministic**, as is `STRUUID`.

Ordering guarantees:

- Argument evaluation is depth-first in document order (§3.2); an operation's
  effects happen after all its arguments' effects.
- Sequence elements evaluate in order: all effects of element *n* happen
  before any effect of element *n+1*.
- `ForEach` yields its result sequence in item order. Whether iterations
  execute sequentially or concurrently is implementation-defined; a program
  must not rely on effect ordering *across* iterations (within one iteration,
  sequence ordering applies). The Python implementation is currently
  sequential.

There are no transactions: if evaluation fails midway, effects already
performed are not rolled back.

### 3.7 Errors

Failures raise Python exceptions per this table (normative):

| Condition | Exception |
|-----------|-----------|
| unknown operation name in `@op` | `ValueError` |
| envelope without `program` | `ValueError` |
| `null` form | `TypeError` |
| missing required argument key | `KeyError` |
| argument or operand of the wrong type (any layer) | `TypeError` |
| unknown variable in `$name` lookup | `ValueError` |
| context lookup miss, or no context established | `ValueError` |
| `Filter` position < 1 or > length | `ValueError` |
| regular-expression errors in `Replace` — invalid pattern or flags, zero-length-matching pattern, invalid replacement (XPath `err:FORX000*`) | `ValueError` |
| unknown `type` in SPARQL JSON term form | `ValueError` |
| blank node where SPARQL syntax forbids it (`Values` data) | `ValueError` |
| HTTP/SPARQL transport failure | `urllib.error.HTTPError` / `URLError`, unwrapped |

Type checking is strict: operations validate their inputs and raise `TypeError`
*before* performing any effect. No implicit casting is performed between Term
kinds; the only implicit conversion anywhere is scalar coercion (§2.2) and
string-compatibility (§4.2).

## 4. Operation Catalog (normative)

Catalog entry conventions: the *Abstract* signature is in the type language of
§1.1; *JSON args* lists the argument keys of the JSON serialization with their
expected value types after evaluation; ⟨quoted⟩ marks quoted operands (§3.3).
`Maybe τ` marks optional arguments. Effects per §3.6 are noted when not pure.

### 4.1 Control flow, variables, context

**ForEach** — evaluate an operation once per item of a sequence or per row of
a SPARQL result; the item is the context (§3.5).
```
Abstract: (Sequence α + Result) × Operation⟨quoted⟩ → Sequence β
Python:   execute_json only (interpreter-level special form)
JSON:     select: Sequence α + Result · operation⟨quoted⟩: form or array of forms
```
- Iterates a `Sequence` item-by-item, a `Result` row-by-row in result order.
  Any other `select` value raises `TypeError`.
- Each iteration runs in a fresh variable scope with the item as context.
- If `operation` is an array, its forms evaluate in order within the
  iteration's scope and the iteration's value is the *last* non-Unit value.
- Iteration values that are Unit (`None`) are dropped from the output;
  sequence-valued iteration results are kept nested (no flattening). Output
  length therefore equals input length minus Unit-valued iterations.

**Filter** — positional selection from a sequence, XSLT-style.
```
Abstract: (Sequence α + Result) × Position → α
Python:   def execute(self, input_data: Any, expression: Any) -> Any
JSON:     input: Sequence α + Result · expression: Position
```
- 1-based. A `Result` input is treated as its row sequence (yields a
  `Binding`). Position < 1 or > length raises `ValueError`; a non-integer
  expression raises `TypeError`. Only positional expressions are defined in
  this version of the algebra.

**Bindings** — project a SPARQL result to its row sequence.
```
Abstract: Result → Sequence Binding
Python:   def execute(self, table: Result) -> List[Dict[str, Node]]
JSON:     table: Result
```
- Order-preserving; an empty result yields the empty sequence.

**Variable** — bind a name in the current scope (like `xsl:variable`).
```
Abstract: String × Any → Unit
Python:   def execute(self, name: str, value: Any, variable_stack: list) -> None
JSON:     name: String (plain JSON string, not a form) · value: any form
```
- Binds in the innermost scope (§3.4). The JSON layer returns Unit (`None`);
  in a `ForEach` operation array, Unit values do not become the iteration's
  value.

**Value** — read a variable (`$name`) or a context member (`name`). §3.4–3.5.
```
Abstract: String → Any
Python:   def execute(self, name: str, context: Any, variable_stack: list) -> Any
JSON:     name: String (plain JSON string; `$` prefix selects variable lookup)
```

**Current** — the context item itself (like XSLT `current()`).
```
Abstract: () → Context
Python:   def execute(self, current_item: Any) -> Any
JSON:     (no arguments)
```
- Raises `ValueError` when no context is established (§3.5).

**Execute** — evaluate a quoted operation form in the current context and
environment.
```
Abstract: Operation⟨quoted⟩ → Any
Python:   def execute(self, operation: Any) -> Any
JSON:     operation⟨quoted⟩: an operation-call form
```
- The operand must be an operation-call object (`TypeError` otherwise). Its
  purpose is indirection: the operand may be assembled or selected at runtime
  (e.g. read from a variable) before being evaluated.

### 4.2 String and term operations

Operations in this section are named after SPARQL 1.1 / XPath F&O functions
and follow those definitions exactly — including their signatures (e.g.
`simple literal STR(literal ltrl)` / `simple literal STR(IRI rsrc)`); the
summaries below are paraphrases, and where they fall short the W3C text is
normative. A SPARQL *simple literal* is materialized as an rdflib `Literal`
with no datatype and no language tag — exactly as rdflib's own SPARQL engine
does — and under RDF 1.1 denotes the same value as the corresponding
`xsd:string` literal.

String-compatibility rule: where an operation is documented as accepting a
*string-compatible* Literal it accepts `xsd:string` literals, language-tagged
literals, and plain literals; any other Term raises `TypeError` (use `Str` to
cast explicitly).

**Str** — the lexical form of a Term, per SPARQL 1.1 `STR()`:
`simple literal STR(literal ltrl)` / `simple literal STR(IRI rsrc)`.
```
Abstract: (URI + Literal) → Literal
Python:   def execute(self, term: Node) -> Literal
JSON:     input: URI + Literal
```
- Returns the lexical form of a Literal, or the codepoint representation of a
  URI, as a **simple literal**. As in SPARQL, the language tag is **not**
  carried over. A `BNode` raises `TypeError` (a SPARQL type error), as does
  any non-Term.

**Concat** — per SPARQL 1.1 `CONCAT()`:
`string literal CONCAT(string literal ltrl1 ... string literal ltrln)`.
```
Abstract: Sequence Literal → Literal
Python:   def execute(self, inputs: List[Literal]) -> Literal
JSON:     inputs: array of string-compatible Literal forms
```
- Result kind per SPARQL: if all inputs are typed `xsd:string`, so is the
  result; if all inputs carry the *same* language tag, the result carries it
  too; in all other cases (including the empty input sequence) the result is
  a simple literal.

**Replace** — per SPARQL 1.1 `REPLACE()` / XPath `fn:replace`:
`string literal REPLACE(string literal arg, simple literal pattern,
simple literal replacement [, simple literal flags])`.
```
Abstract: Literal × Literal × Literal × Maybe Literal → Literal
Python:   def execute(self, input_str, pattern, replacement, flags=None) -> Literal
JSON:     input: string-compatible Literal · pattern · replacement · flags:
          language-tag-free string Literals (simple literals)
```
- Per the signature, `pattern`, `replacement` and `flags` are simple
  literals: a language-tagged value there raises `TypeError`. `input` may be
  any string literal.
- Pattern and `flags` (`s`, `m`, `i`, `x`, `q`) per XPath `fn:replace`. In the
  replacement string, `$N` references capture group *N*, `\$` is a literal
  dollar, and `\\` is a literal backslash; any other use of `\` or `$` is an
  error.
- Per the SPARQL string-function convention, the result is a string literal
  of the same kind as `arg` (its datatype and language tag are carried over).
- Errors (`ValueError`, mirroring XPath `err:FORX000*`): invalid flags, an
  invalid pattern, a pattern that matches the zero-length string, or an
  invalid replacement string.

**EncodeForURI** — percent-encode a string for use inside a URI, per SPARQL
`ENCODE_FOR_URI` / XPath `fn:encode-for-uri`.
```
Abstract: Literal → Literal
Python:   def execute(self, input_str: Literal) -> Literal
JSON:     input: string-compatible Literal
```
- Every character except the RFC 3986 unreserved set
  (`A–Z a–z 0–9 - . _ ~`) is percent-encoded (UTF-8). Per the signature
  `simple literal ENCODE_FOR_URI(string literal ltrl)`, the result is a
  simple literal.

**STRUUID** — fresh UUID string, per SPARQL `STRUUID()`. Non-deterministic.
```
Abstract: () → Literal
Python:   def execute(self) -> Literal
JSON:     (no arguments)
```
- A simple literal (per the signature `simple literal STRUUID()`) holding an
  RFC 4122 version-4 UUID in lowercase hyphenated form. Successive
  invocations differ.

**URI** — cast a Term to a URI, like SPARQL `URI()`/`IRI()`.
```
Abstract: (URI + Literal) → URI
Python:   def execute(self, term: Node) -> URIRef
JSON:     input: URI + Literal
```
- A URI input is returned as-is; a Literal yields the URI of its lexical
  form. A `BNode` raises `TypeError` (a blank node has no IRI). The lexical
  form is *not* validated against RFC 3986; garbage in, garbage out.

**ResolveURI** — RFC 3986 reference resolution.
```
Abstract: URI × Literal → URI
Python:   def execute(self, base: URIRef, relative: Literal) -> URIRef
JSON:     base: URI · relative: string-compatible Literal
```
- Standard §5 resolution semantics (as by `urljoin`): if `relative` is itself
  an absolute URI, the result is `relative`.

### 4.3 SPARQL operations

**SELECT** — execute a SPARQL SELECT query against an endpoint. *Query* effect.
```
Abstract: URI × Literal → Result
Python:   def execute(self, endpoint: URIRef, query: Literal) -> Result
JSON:     endpoint: URI · query: string Literal (simple or xsd:string)
```
- Types are validated before any network I/O.

**CONSTRUCT** — execute a SPARQL CONSTRUCT query. *Query* effect.
```
Abstract: URI × Literal → Graph
Python:   def execute(self, endpoint: URIRef, query: Literal) -> Graph
JSON:     endpoint: URI · query: string Literal (simple or xsd:string)
```

**DESCRIBE** — execute a SPARQL DESCRIBE query. *Query* effect.
```
Abstract: URI × Literal → Graph
Python:   def execute(self, endpoint: URIRef, query: Literal) -> Graph
JSON:     endpoint: URI · query: string Literal (simple or xsd:string)
```

**Substitute** — textually substitute one SPARQL variable with a Term.
```
Abstract: Literal × Literal × (URI + Literal) → Literal
Python:   def execute(self, query, var, binding_value) -> Literal
JSON:     query: Literal · var: Literal (variable name, with or without `?`)
          · binding: URI + Literal (Term or SPARQL JSON term form, §2.4)
```
- Matches both `?var` and `$var` occurrences at token boundaries. A URI value
  serializes as `<iri>`; a Literal as a quoted literal with its language tag
  or datatype. A `BNode` value raises `TypeError` (a blank-node label in a
  query is a fresh variable, not a reference — substitution would be
  meaningless).
- The substitution is textual, not parse-aware; it can produce an invalid
  query if `var` collides with content inside string literals of the query.
  Prefer `Values` where applicable.

**Values** — append a SPARQL `VALUES` data block built from a result set.
```
Abstract: Literal × Result × Maybe (Sequence String) → Literal
Python:   def execute(self, query: Literal, data: Result,
                      vars: Optional[List[str]] = None) -> Literal
JSON:     query: Literal · data: Result · vars: Maybe (array of String)
```
- Columns default to the result's variables; `vars` selects/reorders them
  (names given with or without `?`). Missing values render as `UNDEF`. Terms
  serialize per SPARQL syntax with correct escaping. Blank nodes raise
  `ValueError` (forbidden in `VALUES`).

**SPARQLString** — generate a SPARQL query string from natural language via an
LLM. *Non-deterministic*; external service call.
```
Abstract: Literal → Literal
Python:   def execute(self, question: Literal) -> Literal
JSON:     question: Literal
```
- Only the type contract is normative: string-compatible Literal in, Literal
  out. The generated query text is not specified.

### 4.4 Linked Data (HTTP) operations

`POST`, `PUT` and `PATCH` return a single-row `Result` with variables
`status` (`xsd:integer` HTTP status) and `url` (the effective request URI).
Transport failures propagate per §3.7.

**GET** — dereference a URI to an RDF graph. *Query* effect.
```
Abstract: URI → Graph
Python:   def execute(self, url: URIRef) -> Graph
JSON:     url: URI
```

**POST** — append RDF data to a resource. *Update* effect.
```
Abstract: URI × Graph → Result
Python:   def execute(self, url: URIRef, data: Graph) -> Result
JSON:     url: URI · data: Graph or RDF data form (parsed with base = url)
```

**PUT** — replace a resource's RDF representation. *Update* effect.
```
Abstract: URI × Graph → Result
Python:   def execute(self, url: URIRef, data: Graph) -> Result
JSON:     url: URI · data: Graph or RDF data form (parsed with base = url)
```

**PATCH** — apply a SPARQL Update to a resource. *Update* effect.
```
Abstract: URI × Literal → Result
Python:   def execute(self, url: URIRef, update: Literal) -> Result
JSON:     url: URI · update: Literal (SPARQL Update string)
```

### 4.5 Graph operations

**Merge** — union of graphs.
```
Abstract: Sequence Graph → Graph
Python:   def execute(self, graphs: List[Graph]) -> Graph
JSON:     graphs: array of Graph or RDF data forms
```
- Set union of triples: duplicate triples collapse. Blank-node labels are
  taken as-is (this is graph union, not RDF merge — graphs sharing a label
  will coalesce on it). Input order is irrelevant to the result.

### 4.6 Schema operations

All take `endpoint`, the URI of a **SPARQL endpoint**, query instance data
there, and return an ontology `Graph`. *Query* effect.

**ExtractClasses** — `URI → Graph`. Classes present in the data
(`owl:Class` candidates), from `rdf:type` usage. JSON: `endpoint: URI`.

**ExtractDatatypeProperties** — `URI → Graph`. `owl:DatatypeProperty`
candidates from literal-valued predicates. JSON: `endpoint: URI`.

**ExtractObjectProperties** — `URI → Graph`. `owl:ObjectProperty` candidates
from IRI-valued predicates; infers `owl:FunctionalProperty` when the maximum
number of objects per subject is 1 (closed-world over the present triples).
JSON: `endpoint: URI`.

**ExtractOntology** — `URI → Graph`. The union of the three extractions
above: classes plus datatype and object properties, as one graph.
JSON: `endpoint: URI`.

## 5. Conformance notes

- The JSON serialization here and the XML serialization used by REST-VKG are
  two concrete syntaxes of the same abstract algebra; operation names and
  abstract signatures are shared. Operations currently exclusive to one
  implementation (e.g. `Iterate` in REST-VKG; `PATCH`, `Values`, `Filter`,
  `Bindings`, `URI` and the schema operations here) are slated for parity.
- MCP exposure (`mcp_run`) is an interface adapter, not part of the algebra;
  its plain-JSON conversions are implementation detail.

---

## Appendix A — LinkedDataHub extension operations (informative)

The `ldh-*` operations target a LinkedDataHub instance and compose the core
operations above (mostly `PUT`/`POST`/`PATCH` with LDH vocabularies). Their
return contracts are intentionally loose in this revision and are *not*
normative; they will be pinned in a later revision. All are *update* effects
unless noted.

| Operation | JSON args (`Maybe` = optional) |
|-----------|--------------------------------|
| `ldh-CreateContainer` | `parent: URI · title: Literal · slug: Maybe Literal · description: Maybe Literal` |
| `ldh-CreateItem` | `container: URI · title: Literal · slug: Maybe Literal` |
| `ldh-List` *(query)* | `url: URI · endpoint: URI` (or `base: Literal`, from which `endpoint` = `base` + `sparql`) |
| `ldh-AddFile` | `url: URI · file: Literal (path) · title: Literal · description: Maybe Literal · content_type: Maybe Literal` |
| `ldh-AddGenericService` | `url: URI · endpoint: URI · title: Literal · description/fragment: Maybe Literal · graph_store: Maybe URI · auth_user/auth_pwd: Maybe Literal` |
| `ldh-AddResultSetChart` | `url: URI · query: URI · title: Literal · chart_type: URI · category_var_name: Literal · series_var_name: Literal · description/fragment: Maybe Literal` |
| `ldh-AddSelect` | `url: URI · query: Literal · title: Literal · description/fragment: Maybe Literal · service: Maybe URI` |
| `ldh-AddView` | `url: URI · query: URI · title: Literal · description/fragment: Maybe Literal · mode: Maybe URI` |
| `ldh-AddObjectBlock` | `url: URI · value: URI · title/description/fragment: Maybe Literal · mode: Maybe URI` |
| `ldh-AddXHTMLBlock` | `url: URI · value: Literal (XHTML) · title/description/fragment: Maybe Literal` |
| `ldh-RemoveBlock` | `url: URI · block: Maybe URI` |
| `ldh-GenerateOntologyViews` | `ontology: Graph · base_uri: URI · service_uri: URI` |
| `ldh-GenerateClassContainers` | `ontology: Graph · parent_container: URI · endpoint: URI · service_uri: Maybe URI` |
| `ldh-GeneratePortal` | `endpoint: URI · ontology_namespace: URI · parent_container: URI` |
