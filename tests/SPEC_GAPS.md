# Web Algebra spec gaps

This file tracks ambiguities and omissions in `formal-semantics.md` discovered while
authoring the test suite. Tests that depend on an unresolved item are marked
`pytest.skip(...)` until the spec settles the question.

The 2026-07 spec rewrite (evaluation semantics, error taxonomy, per-operation JSON
argument tables) resolved the bulk of the original entries; the resolution record is
kept below so the decisions stay traceable. Only the **Remaining gaps** section is
live.

---

## Remaining gaps

- **`ldh-*` operations** — Appendix A of the spec is informative. It now pins the
  return of the *update* operations (the single-row `Result` of §4.4) and makes
  them subject to §3.6/§4.4, and `ldh-AddSelect`/`ldh-AddConstruct` are unit-tested
  against stubbed HTTP on that basis (return shape, recorded `sp:Select` /
  `sp:Construct`, non-2xx → `ValueError`). The remaining `ldh-*` unit tests stay
  type-only; their behavior is exercised by the `ldh`-marked integration fixtures
  against a live LinkedDataHub.
- **SPARQLString** — §4.3 now pins `endpoint · question · projection · context`.
  The type contract and the empty-`context` `ValueError` are tested offline. The
  model-dependent contract (parseable simple-literal result, projection honoured,
  bounded retry then `ValueError`) needs the model call stubbed, and there is no
  infrastructure seam for SPARQLString's model call outside the operation module,
  so those tests are skipped.
- **Relative IRIs in a `graph` data form** (§4.3) — the form "is parsed with no
  base IRI, so its IRIs must be absolute", but what a relative IRI does (error,
  dropped triple, left relative) is unstated. Test skipped (`test_select.py`).
- **Live-service behavior** — §3.7 pins transport failures to
  `urllib.error.HTTPError`/`URLError` propagating unwrapped, and §4.3–4.4 pin the
  response contract (RDF-only, transparent conneg, non-RDF → `ValueError`); still
  unspecified: timeouts, retry policy beyond 429, and redirect handling beyond 308.
- **XPath regex dialect coverage** — `Replace` compiles patterns with Python's `re`.
  The common syntax is shared with XPath regular expressions, but XPath-only
  constructs (`\p{...}` category escapes, `\i`/`\c`, character-class subtraction
  `[a-z-[aeiou]]`) are not supported and surface as `ValueError` (invalid pattern).
  This is an implementation gap against the normative fn:replace behavior, not
  sanctioned spec behavior.

## Resolved in the 2026-10 spec revision

These supersede the corresponding 2026-07 entries below.

- **Flat sequences** (§3.1, §3.2, §3.8 SEQ): sequences are XDM-flat; Unit and
  `Variable` leave no item, a sequence-valued element contributes its items, and a
  `Result` is one item (never dissolved). Supersedes "sequence-valued results stay
  nested" under *ForEach output shape*.
- **ForEach / Iterate results** (§4.1): the concatenation of the iteration values;
  an array `operation` yields the concatenation of its element values per
  iteration. Supersedes "operation arrays yield the last non-Unit value".
- **Same-target rule** (§3.6): two iterations of one `ForEach` updating the same
  reported URI → `ValueError`, raised when the second write is reported; nested
  `ForEach` writes count for every enclosing iteration.
- **Filter by name** (§4.1): a string Literal on a `Binding` looks the variable up
  (bare, `?x`, `$x`); a miss → `ValueError`; other pairings → `TypeError`.
  Supersedes *Filter signature* below.
- **SELECT/CONSTRUCT/DESCRIBE `graph` operand** (§4.3): exactly one of
  `endpoint`/`graph`; neither → `KeyError`, both → `TypeError`; `graph` is pure.
- **Write contract** (§4.4, §3.7): single-row `Result` (`status`, `url` = Location
  or effective request URI); non-2xx write → `ValueError`, non-2xx read →
  `HTTPError`; `If-Match` from a `HEAD` with the write's `Accept`.
- **Relative `Location`** (§4.4): resolved against the effective request URI
  (RFC 3986 §5).
- **SPARQLString empty `context`** (§4.3): the `ValueError` is raised before the
  model is called.
- **Schema `bindings`** (§4.6): optional `Result` whose `subject` column scopes the
  extraction via `VALUES`; no `subject` / no rows → `ValueError`, non-Result →
  `TypeError`.

## Resolved in the 2026-07 spec revision

Each item below is now normative in `formal-semantics.md` (section in parentheses),
and the corresponding tests are un-skipped.

- **Catalog omissions**: `Concat` (§4.2) and `ExtractOntology` (§4.6) added.
- **W3C conformance rule** (§4.2 preamble): operations named after SPARQL 1.1 /
  XPath functions follow those definitions *by normative reference*, signatures
  included; simple literals are materialized as plain rdflib literals (no
  datatype), exactly as rdflib's own SPARQL engine does.
- **Str** (§4.2): per `simple literal STR(literal ltrl)` / `simple literal STR(IRI
  rsrc)` — lexical form / codepoint representation as a simple literal; language
  tags are not carried over; BNode → `TypeError` (SPARQL type error).
- **Concat** (§4.2): per SPARQL `CONCAT()` result-kind rules — all `xsd:string` →
  `xsd:string`; all same language tag → that tag; otherwise simple literal.
- **Replace** (§4.2): per SPARQL `REPLACE()` / `fn:replace` — optional `flags`
  argument (`s m i x q`), `$N` capture-group references with `\$`/`\\` escapes,
  `err:FORX000*` conditions → `ValueError`, result kind follows the first argument,
  and `pattern`/`replacement`/`flags` must be simple literals.
- **URI on BNode / invalid lexical form** (§4.2): BNode → `TypeError`; lexical forms
  are not validated against RFC 3986.
- **EncodeForURI character set** (§4.2): percent-encode everything outside the
  RFC 3986 unreserved set (`A–Z a–z 0–9 - . _ ~`), per XPath `fn:encode-for-uri`;
  result is a simple literal.
- **STRUUID format** (§4.2): simple literal; RFC 4122 version-4, lowercase
  hyphenated.
- **Substitute** (§4.3): matches `?var` and `$var` at token boundaries; URI → `<iri>`,
  Literal → quoted with lang/datatype; BNode → `TypeError`; substitution is textual
  and documented as not parse-aware.
- **Merge duplicate semantics** (§4.5): set union; duplicates collapse; blank-node
  labels taken as-is (graph union, not RDF merge).
- **Bindings order/empty** (§4.1): order-preserving; empty result → empty sequence.
- **Filter signature** (§4.1): `(Sequence α + Result) × Position → α` — the old
  `→ α` was correct for the positional case, which is the only expression kind this
  version defines; non-integer expressions → `TypeError`, out-of-range → `ValueError`.
- **ForEach output shape** (§4.1): Unit-valued iterations dropped; sequence-valued
  results stay nested; operation arrays yield the last non-Unit value; Result rows
  iterate in result order; fresh variable scope per iteration.
- **ForEach pure layer** (§4.1): declared an interpreter-level special form —
  `execute_json` only; no pure `execute()` contract.
- **Variable return type** (§4.1): `⊥` corrected to `Unit`; JSON layer returns
  `None`; binds in the innermost scope, rebinding overwrites; scope creation belongs
  to sequences and ForEach iterations (§3.4), not to Variable.
- **Value context shapes & precedence** (§3.5, §4.1): Binding → bound term, mapping →
  member value, other object → attribute; the `$` sigil selects the lookup domain, so
  variables and context never shadow; misses → `ValueError`.
- **Current on unset context** (§3.5): `ValueError` — only ForEach establishes a
  context.
- **Execute** (§4.1): removed from the algebra — it was the MCP-era entry point
  and no document uses it.
- **Extract\* URI role** (§4.6): the URI names a SPARQL endpoint.
- **Error semantics** (§3.7): normative exception table — unknown `@op` →
  `ValueError`, type mismatch → `TypeError`, missing required argument → `KeyError`,
  unknown variable / context miss → `ValueError`, `null` form → `TypeError`,
  transport failures propagate unwrapped.
- **JSON dispatch surface**: every core operation's argument keys are now normative
  (§4 catalog, per-entry `JSON:` line); `ldh-*` keys documented informatively
  (Appendix A).
- **Strict-typing divergences observed on first run** (Str, SELECT): resolved on the
  implementation side — both validate input types before any effect (§3.7).
- **Linked Data response contract** (§4.3–4.4): the HTTP operations are RDF-specific
  and symmetric — they read and write RDF graphs; content negotiation is transparent
  in the implementation; a non-RDF response (unsupported media type, missing
  `Content-Type`, or a body that does not parse as the negotiated format) raises
  `ValueError`.
- **Value-domain precision** (§3.1): the former `JSON` summand split into `Object`
  (generic-object results, members are Values) and `Data` (RDF data forms, holes are
  Terms, the rest raw JSON), with their conversion boundaries stated.
- **Result persistence** (§1.1): Result values are materialized and re-iterable.
- **Value focus-item lookup** (§3.5): closed to `Binding` + mapping; the former
  host-reflection (attribute) fallback removed.
