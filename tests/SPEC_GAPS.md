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

- **`ldh-*` operations** — Appendix A of the spec is explicitly informative: JSON arg
  keys are documented, but return contracts are deliberately loose (`Any`, or
  `Result` with unspecified shape). Unit tests for these operations stay skipped
  until a later spec revision pins them; behavior is exercised by the `ldh`-marked
  integration fixtures against a live LinkedDataHub.
- **SPARQLString** — §4.3 pins the type contract only (string-compatible Literal →
  Literal); the operation is non-deterministic (LLM) and needs an OpenAI client, so
  even the type contract is only exercised in live runs.
- **Live-service behavior** — §3.7 pins transport failures to
  `urllib.error.HTTPError`/`URLError` propagating unwrapped, but content negotiation,
  redirects (beyond 308), timeouts, and retry policy remain unspecified.

## Resolved in the 2026-07 spec revision

Each item below is now normative in `formal-semantics.md` (section in parentheses),
and the corresponding tests are un-skipped.

- **Catalog omissions**: `Concat` (§4.2) and `ExtractOntology` (§4.6) added.
- **Str result datatype** (§4.2): string-compatible literals pass through unchanged
  (language tags preserved — documented divergence from SPARQL `STR()`); other Terms
  → `xsd:string` of the lexical/IRI form.
- **URI on BNode / invalid lexical form** (§4.2): BNode → `TypeError`; lexical forms
  are not validated against RFC 3986.
- **EncodeForURI character set** (§4.2): percent-encode everything outside the
  RFC 3986 unreserved set (`A–Z a–z 0–9 - . _ ~`), per XPath `fn:encode-for-uri`.
- **Replace pattern dialect** (§4.2): regular expression, Python `re` dialect
  (documented divergence from SPARQL's XPath/XQuery regex).
- **STRUUID format** (§4.2): RFC 4122 version-4, lowercase hyphenated, `xsd:string`.
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
- **Execute narrative** (§4.1): evaluates a quoted operation form in the current
  context and the current variable environment.
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
