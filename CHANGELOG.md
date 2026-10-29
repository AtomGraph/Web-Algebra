# Changelog

All notable changes to Web Algebra are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). The normative definition of every
operation is [formal-semantics.md](formal-semantics.md).

## [Unreleased]

### Added

- **`Reconcile`** (formal-semantics.md §4.7): the candidates a reconciliation
  service offers for a name, as a `Result` of `entity`, `name`,
  `description`, `score` and `match`, best first. It speaks the W3C Entity
  Reconciliation Service API to any `endpoint` — Wikidata's is one — with an
  optional `type` id and `limit`; the manifest's `identifierSpace` resolves the
  candidate ids to URIs. The XML serialization's executor has it too, so the
  two serializations keep the same catalog.

## [2.0.3] - 2026-10-29

### Changed

- **`ldh-CreateContainer` and `ldh-CreateItem` only create**: the `PUT`
  carries `If-None-Match: *` and no `If-Match`, as LinkedDataHub's CLI create
  commands and its client's create forms send it, so a document already at
  the URI is refused `412` and left as it is, and the operation fails. They
  read the document's entity tag and quoted it before, which made a create on
  an existing URI replace the document whole, its content blocks with it. A
  new `if_absent` argument (xsd:boolean) accepts the existing document as the
  result instead, like `mkdir -p`, and does not count it as a write to an
  enclosing `ForEach`. Their kind is `write`, no longer `destructive`. A
  pipeline that relied on a create replacing a document `PUT`s it;
  `ldh-GenerateClassContainers`, which creates through `ldh-CreateItem`, now
  stops on a class whose item already exists instead of replacing it.

## [2.0.2] - 2026-10-28

### Added

- **A release lists itself in the MCP Registry**: the release workflow
  publishes `server.json` after the PyPI upload, logged in with GitHub OIDC.
  Run by hand with a released tag, it publishes that tag's `server.json` and
  nothing else.

### Changed

- **`ldh-AddView` says what each mode is for**: a view shows resources, and
  its mode is picked by what they carry — `GridMode` a card per resource led
  by its image, `MapMode` a pin per resource with `geo:lat`/`geo:long`,
  `GraphMode` the links between them. **`ldh-AddResultSetChart`** says a chart
  shows values (aggregates, measurements), so things, people and places belong
  in a view.

### Fixed

- **`ldh-AddView` no longer claims every projected variable is DESCRIBE'd**:
  LinkedDataHub describes the resources the first projected variable binds,
  so that variable must bind resources.

## [2.0.1] - 2026-10-21

### Added

- **`web-algebra mcp`** runs the MCP server on stdio, as `web-algebra-mcp`
  does. The MCP Registry entry (`server.json`) runs it: a registry client
  starts a PyPI package as `uvx web-algebra`, which on its own starts the
  planner.

## [2.0.0] - 2026-10-21

Web Algebra now has a formal semantics, and the Python implementation conforms
to it. The evaluation model is XSLT/XPath applied to RDF: SPARQL supplies the
data model and the term-level functions. The JSON serialization here and the
XML serialization in [REST-VKG](https://github.com/AtomGraph/REST-VKG) are two
syntaxes of the same algebra. Most of the changes below follow from that, and
many are breaking.

### Breaking

- **`Execute` is removed.** It was the MCP-era "run this program" operation and
  is the identity in the algebra.
- **`STRUUID` is renamed `StrUUID`**, by the naming rule the spec now states
  (§4): operations are PascalCase, a SPARQL or XPath function's name included
  (`STR` → `Str`, `STRUUID` → `StrUUID`), and only the HTTP methods and SPARQL
  query forms keep upper case. `STRUUID` remains a deprecated alias, so 1.x
  plans still run.
- **Sequences are flat** (XDM): the sequence form, `ForEach` and `Iterate`
  yield the concatenation of their values, and `Unit` (what `Variable`
  returns) is the empty sequence, contributing nothing. A `Result` is never
  dissolved into its rows. An array argument such as `Concat`'s `inputs` or
  `SPARQLString`'s `context` is a sequence form too, so a sequence-valued
  element contributes its items.
- **The document envelope** (`{"@web-algebra": …, "program": […]}`) is
  removed: a document is a single form or an array of steps.
- **`Substitute` and `Values` restrict variables instead of replacing them**
  (after A. Seaborne's [Substitution](https://afs.github.io/substitute.html)
  note). A variable stays a variable: an inline `VALUES` block with the given
  values is joined into every group of the query or update, subqueries that
  do not project it keep their own copy, and assigning it (`AS`, `VALUES`) is
  a `ValueError`. Queries stay valid, `SELECT ?x` still projects `?x`, and
  every result row carries it. `Values` no longer appends a trailing `VALUES`
  clause. ([#38](https://github.com/AtomGraph/Web-Algebra/pull/38))
- **String and term operations follow SPARQL 1.1 / XPath F&O exactly:**
  - `Str` returns a simple literal without the language tag, and raises
    `TypeError` for a blank node.
  - `Concat` follows `CONCAT()`'s result-kind rules.
  - `EncodeForURI` and `StrUUID` return simple literals.
  - `Replace` is XPath's `fn:replace`: XSD regular-expression syntax (`\p{L}`,
    `\i`, character-class subtraction; `$` anchors at the end of the string),
    the flags `s m i x q` (`x` removes whitespace, and `#` is literal), the
    replacement rules (`$N` beyond the groups is the empty string or a literal
    digit), and `err:FORX0001`–`0004` as `ValueError`. Python-only syntax such
    as `(?P<n>…)` is refused. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
  - `ResolveURI` follows RFC 3986 §5.2 for a base of any scheme (`urn:a:b` +
    `#f` is `urn:a:b#f`), where it used to return the reference unchanged for
    schemes `urllib` does not know. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **`Value`** looks a bare name up only in a `Binding` or a mapping. A name
  that is missing, or a variable an `OPTIONAL` left unbound, is a
  `ValueError`; it used to silently yield nothing. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **`SELECT`, `CONSTRUCT` and `DESCRIBE`** take exactly one of `endpoint` or
  `graph` (a graph in hand, queried locally), and refuse a query of another
  form with `ValueError` before any network I/O. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **Writes:**
  - A `POST`, `PUT` or `PATCH` (or `ldh-*` write) answered outside 2xx raises
    `WriteRefusedError`, a `ValueError`, and nothing after it runs.
  - A write does not follow a redirect: a 3xx is an error, except `303 See
    Other`, which reports success with `url` = its `Location`. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
  - A write's `url` is the response's `Location`, resolved against the request
    URI, or else the request URI.
- **Two updates to the same URI within one `ForEach`** (from different
  iterations) are an error (`SameTargetError`).
- **`ldh-CreateContainer` / `ldh-CreateItem`** use a random UUID when no
  `slug` is given, as the LinkedDataHub CLI does. They used the title, so a
  repeated title replaced an existing document. ([#32](https://github.com/AtomGraph/Web-Algebra/pull/32))
- **`ldh-List`** returns a `Result` (rows with `child` and `thing`), so
  `ForEach` can iterate it; it returned a dict. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **`ldh-AddFile`'s `url`** is the uploaded file's URI, read back from the
  document by its `foaf:sha1`; it was built as `scheme://host/uploads/…`,
  which is wrong when the application's base URI has a path. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **The `dh:` vocabulary** is LinkedDataHub's
  `https://w3id.org/atomgraph/linkeddatahub/document-hierarchy#`, no longer
  the retired LDT namespace. ([#26](https://github.com/AtomGraph/Web-Algebra/pull/26))
- **Errors** follow the spec's categories (`TypeError` / `ValueError` /
  `KeyError`), raised as subclasses of `WebAlgebraError` that also inherit
  the built-in, e.g. `UnknownOperationError`, `VariableNotFoundError`,
  `NoFocusError`, `WriteRefusedError`.
- **rdflib** 7.6, from 7.0.0. ([#39](https://github.com/AtomGraph/Web-Algebra/pull/39))
- **MCP SDK 2.x**, from 1.10.1, which clears its security advisories and those
  of the packages it brought in (Starlette, AnyIO, python-multipart, …). The
  HTTP transport is at `/mcp`. The server no longer offers resources: its one
  resource listing failed on every call.
- **Dependencies are ranges**, not exact pins, so the package installs beside
  others; `uv.lock` keeps the development environment reproducible.

### Added

- **The `ldh-*` operations take the LinkedDataHub CLI's options**, and write
  them as the CLI of LinkedDataHub 6.2.3 does: `ldh-CreateContainer`
  `children_view` and `primary_topic`; `ldh-CreateItem` `description` and
  `primary_topic`; `ldh-AddObjectBlock` `graph`; several series for
  `ldh-AddResultSetChart`; and `ldh-AddView` `show_when_empty`. A view's `mode` may also be `ac:TableMode`
  or `ac:ChartMode`.
  `tests/test_ldh_cli_parity.py` runs each operation against the CLI on a live
  LinkedDataHub and requires the same document.
  ([#61](https://github.com/AtomGraph/Web-Algebra/pull/61))
- **[formal-semantics.md](formal-semantics.md)**: abstract syntax, value
  domains, big-step evaluation rules, effects and ordering, the error table,
  the full catalog with an `Abstract:` signature per operation, and the
  conformance notes for the two serializations. ([#25](https://github.com/AtomGraph/Web-Algebra/pull/25), [#34](https://github.com/AtomGraph/Web-Algebra/pull/34))
- **MCP Registry entry** [server.json](server.json), and a `py.typed`
  marker, so type checkers read the package's annotations.
- **GitHub Releases**, made by the release workflow from the version's
  section of this file.
- **`Now`**: the current date and time as an `xsd:dateTime`, per SPARQL
  `NOW()`: fixed when a run begins, so every `Now` in one run returns the
  same value.
- **`Iterate`**: stateful iteration with parameters, `next-iteration` and
  `break`, after XSLT 3.0's `xsl:iterate`.
- **`Position` and `Last`**: the XPath focus accessors inside `ForEach`.
- **`Filter` by name** on a row (`Filter(Filter(PUT(…), 1), "url")`), as
  XPath's lookup operator.
- **The URI reference form** `{"@id": "…"}` for a URI; a plain JSON string is
  always a literal.
- **`SPARQLString`** takes `endpoint`, `projection` (the variables a `SELECT`
  must project) and `context` (operations whose results show the model what
  the endpoint holds), with a bounded repair loop and an `ASK` check of the
  query's `WHERE` pattern.
- **`ldh-AddConstruct`**, and a `bindings` scope for the `Extract*`
  operations.
- **`web-algebra-mcp`**: a command that starts the MCP server, for
  `uvx --from web-algebra web-algebra-mcp`. ([#28](https://github.com/AtomGraph/Web-Algebra/pull/28))
- **`If-Match`**: every write sends it from a `HEAD` with the write's
  `Accept`, as LinkedDataHub v6 requires of a write to an existing document,
  `ldh-AddFile` and `DELETE` included. ([#33](https://github.com/AtomGraph/Web-Algebra/pull/33))
- **`OperationKind`** (`READ`, `WRITE`, `DESTRUCTIVE`) on every operation;
  `PUT` and `PATCH` are destructive. ([#29](https://github.com/AtomGraph/Web-Algebra/pull/29))
- **Real-world examples** in [examples/](examples/), each with its
  instruction, plan, checks and the result of a run, tested against a live
  LinkedDataHub with `pytest -m ldh`. ([#37](https://github.com/AtomGraph/Web-Algebra/pull/37))

### Changed

- **The operation guide** [src/web_algebra/prompts/system.md](src/web_algebra/prompts/system.md), which the
  model is given, is rewritten and checked by `tests/test_system_prompt.py`
  against each operation's schema and the spec: every example is
  well-formed, runs, and shows its actual result. ([#36](https://github.com/AtomGraph/Web-Algebra/pull/36))
- **The model is `gpt-5.5`** by default, from `gpt-4o-mini`, for both the
  interactive planner and `SPARQLString`, and `OPENAI_MODEL` overrides it; the
  planner used to ignore the setting. The planner no longer asks for JSON mode,
  which admits only an object: a plan of several steps written as an array
  came back as its first step alone. A reply fenced as a Markdown code block
  is read as the plan inside the fence.
- **`ldh-*` titles and descriptions** may carry a language tag, and keep it.
  ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **A `fragment`** may be given with or without its `#`. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **`Substitute`** escapes every SPARQL `ECHAR` character and refuses an IRI
  that SPARQL cannot write. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **An `endpoint` with a query string of its own**
  (`…/sparql?default-graph-uri=…`) is used as given. ([#35](https://github.com/AtomGraph/Web-Algebra/pull/35))
- **The `ldh-Add*` descriptions** say they write a resource into the
  document; only `ldh-AddXHTMLBlock` and `ldh-AddObjectBlock` show something
  on the page. ([#27](https://github.com/AtomGraph/Web-Algebra/pull/27))

- **`web-algebra` reads the certificate** from `CERT_PEM_PATH` and
  `CERT_PASSWORD`, as the MCP server does; `--cert_pem_path` and
  `--cert_password` override them. ([#41](https://github.com/AtomGraph/Web-Algebra/pull/41))

### Fixed

- **`ldh-GenerateOntologyViews` and `ldh-GeneratePortal` make views
  LinkedDataHub v6 shows.** Its client finds a property's views together with
  the property's `rdfs:domain` and `rdfs:range`, which the views graph now
  carries; a property gets an `ldh:inverseView` too, listing what points to
  the resource; and a view is made only for a property with a domain (or, for
  the inverse view, a range), where the client can show it. A generated view
  is hidden while it has no results (`ldh:showWhenEmpty false`). The guide's
  examples write to the namespace ontology document rather than to `/ns`,
  which is its SPARQL endpoint.
- **The prompts are part of the package**, so `web-algebra` without
  `--from-json` runs when installed, not only from a checkout.
- **An MCP tool's error** is the tool's result (`isError`), which the model
  sees, and an unknown tool a protocol error.
- A `GET` follows a `308` on Python 3.10, where `urllib` only learned to from
  3.11.
- The `README` and the guide's examples pass URIs as `{"@id": …}`. The old
  examples, most of which no longer ran, are replaced by [examples/](examples/).

## [1.5.0] - 2026-06-30

### Added

- `Values`: appends a SPARQL `VALUES` block built from a result set to a
  query. ([#24](https://github.com/AtomGraph/Web-Algebra/pull/24))

## [1.4.1] - 2026-06-30

### Fixed

- `Operation.to_graph` accepts a top-level JSON-LD array. ([#23](https://github.com/AtomGraph/Web-Algebra/pull/23))

## [1.4.0] - 2026-06-30

### Changed

- **Breaking:** `GenerateClassContainers`, `GenerateOntologyViews` and
  `GeneratePortal` are renamed `ldh-GenerateClassContainers`,
  `ldh-GenerateOntologyViews` and `ldh-GeneratePortal`. ([#18](https://github.com/AtomGraph/Web-Algebra/pull/18), [#20](https://github.com/AtomGraph/Web-Algebra/pull/20))
- `ldh-GenerateOntologyViews` uses LinkedDataHub's `ldh:view` vocabulary.
  ([#19](https://github.com/AtomGraph/Web-Algebra/pull/19))
- `ldh-GenerateClassContainers` creates items with an instance-list view
  placed by `ldh-AddObjectBlock`, instead of containers.
- JSON-LD is converted to a graph in one place, `Operation.to_graph`, at the
  consuming operation's boundary. ([#22](https://github.com/AtomGraph/Web-Algebra/pull/22))

### Fixed

- `ldh-GeneratePortal`: views for object properties only, functional-property
  inference, and the container view wiring. ([#21](https://github.com/AtomGraph/Web-Algebra/pull/21))
- A nested `@op` inside JSON-LD data is no longer discarded. ([#22](https://github.com/AtomGraph/Web-Algebra/pull/22))

## [1.3.0] - 2026-06-15

### Added

- A top-level JSON-LD object (one carrying `@context`, `@graph`, `@id` or
  `@type`) is recognised as RDF data. ([#17](https://github.com/AtomGraph/Web-Algebra/pull/17))

## [1.2.0] - 2026-06-14

### Added

- `ldh-AddFile`: uploads a local file to a LinkedDataHub document. ([#16](https://github.com/AtomGraph/Web-Algebra/pull/16))

## [1.1.0] - 2026-05-19

### Added

- Retrying an HTTP request answered `429 Too Many Requests`, after its
  `Retry-After`. ([#14](https://github.com/AtomGraph/Web-Algebra/pull/14), [#15](https://github.com/AtomGraph/Web-Algebra/pull/15))
- Unit tests for every operation, a JSON-fixture integration runner, and CI
  on GitHub Actions. ([#13](https://github.com/AtomGraph/Web-Algebra/pull/13))

## [1.0.0] - 2026-05-05

The first release: a JSON DSL of composable RDF operations, run from the
command line or as an MCP server.

- **Linked Data:** `GET`, `POST`, `PUT`, `PATCH`, `Merge`.
- **SPARQL:** `SELECT`, `CONSTRUCT`, `DESCRIBE`, `Substitute`, `SPARQLString`.
- **Control and context:** `ForEach`, `Filter`, `Bindings`, `Variable`,
  `Value`, `Current`, `Execute`.
- **Strings and terms:** `Str`, `Concat`, `Replace`, `EncodeForURI`,
  `STRUUID`, `URI`, `ResolveURI`.
- **Schema extraction:** `ExtractClasses`, `ExtractDatatypeProperties`,
  `ExtractObjectProperties`, `ExtractOntology`.
- **LinkedDataHub:** `ldh-CreateContainer`, `ldh-CreateItem`, `ldh-List`,
  `ldh-AddSelect`, `ldh-AddView`, `ldh-AddResultSetChart`,
  `ldh-AddGenericService`, `ldh-AddObjectBlock`, `ldh-AddXHTMLBlock`,
  `ldh-RemoveBlock`, and `GenerateClassContainers`, `GenerateOntologyViews`,
  `GeneratePortal`.

[2.0.0]: https://github.com/AtomGraph/Web-Algebra/compare/v1.5.0...v2.0.0
[1.5.0]: https://github.com/AtomGraph/Web-Algebra/compare/v1.4.1...v1.5.0
[1.4.1]: https://github.com/AtomGraph/Web-Algebra/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/AtomGraph/Web-Algebra/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/AtomGraph/Web-Algebra/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/AtomGraph/Web-Algebra/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/AtomGraph/Web-Algebra/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/AtomGraph/Web-Algebra/releases/tag/v1.0.0
