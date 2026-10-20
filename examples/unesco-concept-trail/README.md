# unesco-concept-trail

## Instruction

> Show where "Climate change" sits in the UNESCO Thesaurus: at https://localhost:4443/unesco-concept-trail/climate-change/,
> show the concept and then each broader concept in turn, up to the top of the hierarchy, each as a block titled
> with its English name. Read each concept from its own document in the thesaurus.

## Plan

[`plan.json`](plan.json).

- `$trail` ← `ldh-CreateContainer`
- `$doc` ← `ldh-CreateItem`
- `ldh-AddXHTMLBlock`
- `Iterate` (with `Variable`, `GET`, `SELECT`, `Substitute`, `ldh-AddObjectBlock`)
  - `$description` ← `GET`
  - `$label` ← `SELECT` (with `Substitute`)
  - `ldh-AddObjectBlock`

Operations used: `Concat`, `Filter`, `GET`, `Iterate`, `SELECT`, `Substitute`, `URI`, `Value`, `Variable`, `ldh-AddObjectBlock`, `ldh-AddXHTMLBlock`, `ldh-CreateContainer`, `ldh-CreateItem`.

## Result

From a run on 2026-10-21 against LinkedDataHub ee5905b20 at `https://localhost:4443/`, in 1.0 s. Counts and names come from the live sources and may differ on another day; the shape should not.

2 documents under `https://localhost:4443/unesco-concept-trail/`:

| Document | Title | Content blocks, in order | Other resources | Triples |
|---|---|---|---|---|
| `(container)` | UNESCO Thesaurus trails | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | — | 9 |
| `climate-change/` | Climate change: broader terms | 1. text: “The broader terms of Climate change in the UNESCO Thesaurus, from the most specific to the most general.”<br>2. <https://unesco-thesaurus.demo.linkeddatahub.com/concepts/concept4559/#this><br>3. <https://unesco-thesaurus.demo.linkeddatahub.com/concepts/concept207/#this> | — | 18 |

Key data ([`result.rq`](result.rq)):

| step | concept | title |
|---|---|---|
| 1 | https://unesco-thesaurus.demo.linkeddatahub.com/concepts/concept4559/#this | Climate change |
| 2 | https://unesco-thesaurus.demo.linkeddatahub.com/concepts/concept207/#this | Environmental degradation |

## Checks

After the run, these hold on the instance ([`expect/`](expect/)):

- ✅ `trail-starts-at-climate-change`

## Run it

```bash
uv run python src/web_algebra/main.py --from-json examples/unesco-concept-trail/plan.json \
  --cert_pem_path $CERT_PEM_PATH --cert_password $CERT_PASSWORD
```

or with its checks, cleaning up after itself:

```bash
CERT_PEM_PATH=... CERT_PASSWORD=... uv run pytest -m ldh tests/test_examples.py -k unesco-concept-trail
```
