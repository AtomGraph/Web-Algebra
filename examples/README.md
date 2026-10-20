# Examples

Each example is a real task over live Linked Data, answered by a Web Algebra plan that writes its result into a
[LinkedDataHub](https://atomgraph.github.io/LinkedDataHub/) instance. Every one has been run: its `README.md` shows
what the run produced, and its checks say what must hold afterwards.

| Example | The task | What it composes |
|---|---|---|
| [northwind-category-catalogue](northwind-category-catalogue/) | A page per product category: description, picture, live product list | a write's `url` kept with `Variable`; `ForEach` with ordered steps; a stored query bound to a SPARQL service with `Substitute`; text, picture and view blocks |
| [northwind-sales-dashboard](northwind-sales-dashboard/) | Revenue per category as a bar chart, top customers as a table | stored aggregate queries; `ldh-AddResultSetChart`; content blocks in order |
| [northwind-data-quality](northwind-data-quality/) | An audit of companies missing contact data | figures read out of a `SELECT` with `Filter` and written into prose with `Str`/`Concat`; a list of the offenders |
| [unesco-domain-guides](unesco-domain-guides/) | A guide per thesaurus domain, listing its subject areas | `CONSTRUCT` from an endpoint `POST`ed into the instance; views over the copied data; `Replace` with a capture group for slugs |
| [unesco-concept-trail](unesco-concept-trail/) | "Climate change" and its broader concepts, up to the top | `Iterate` with `next-iteration` and `break`; each concept's own document fetched with `GET` and queried in hand |
| [price-list-sync](price-list-sync/) | Product prices updated from a master price list, safe to rerun | a `setup.json` starting state; `ldh-List` → `ForEach`; nested in-hand lookups; `PATCH` built with `Substitute` |
| [city-profiles](city-profiles/) | Profile pages for three Danish cities from DBpedia: picture, population, map | `ForEach` over strings with `Current`; DBpedia documents fetched with `GET`; `CONSTRUCT` over the graph in hand, with `COALESCE` over messy data; a map view |

## Sources

The examples read from sources that answer quickly and reliably: the
[Northwind Traders](https://northwind-traders.demo.linkeddatahub.com/) and
[UNESCO Thesaurus](https://unesco-thesaurus.demo.linkeddatahub.com/) LinkedDataHub demos (SPARQL and document
`GET`s), and single DBpedia resource documents fetched with `GET`. Public SPARQL endpoints such as Wikidata's and
DBpedia's often time out on anything but the smallest query, so no example depends on one.

## Layout

```
examples/<name>/
  instruction.md   the task, in words - what a user would ask
  plan.json        the plan that does it
  setup.json       optional: state the plan starts from
  expect/*.rq      SPARQL ASK queries that hold on the instance after the run
  result.rq        optional: a SELECT of the data worth showing in README.md
  README.md        written from an actual run by scripts/document_examples.py
```

An example writes only beneath its own container, `https://localhost:4443/<name>/`, so it can be run and removed
without touching anything else on the instance.

## Running

One example, against a LinkedDataHub at `https://localhost:4443/` (run `setup.json` first where there is one):

```bash
uv run python src/web_algebra/main.py --from-json examples/city-profiles/plan.json \
  --cert_pem_path ../LinkedDataHub/ssl/owner/cert.pem --cert_password ********
```

All of them, with their checks, removing what they wrote afterwards (`LDH_BASE` selects another instance,
`WA_KEEP_EXAMPLES=1` keeps the results):

```bash
CERT_PEM_PATH=../LinkedDataHub/ssl/owner/cert.pem CERT_PASSWORD=******** \
  uv run pytest -m ldh tests/test_examples.py
```

Without an instance, `uv run pytest tests/test_examples.py` still checks every plan against the operations' schemas
and the spec, that each example stays inside its container, and that its queries parse.

To rewrite the READMEs from a fresh run:

```bash
CERT_PEM_PATH=... CERT_PASSWORD=... uv run python scripts/document_examples.py [name ...]
```
