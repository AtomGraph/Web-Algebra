# unesco-domain-guides

## Instruction

> For each domain of the UNESCO Thesaurus (https://unesco-thesaurus.demo.linkeddatahub.com/sparql), publish a guide
> page under https://localhost:4443/unesco-domain-guides/ that lists the domain's subject areas (micro-thesauri) by
> their English names. Copy the subject areas into the guide, so the list does not depend on the thesaurus being up.

## Plan

[`plan.json`](plan.json).

- `$guides` ← `ldh-CreateContainer`
- `ForEach` (with `SELECT`, `Variable`, `ldh-CreateItem`, `Replace`, `POST`, `CONSTRUCT`, `Substitute`, `ldh-AddXHTMLBlock`, `ldh-AddSelect`, `ldh-AddView`, `ldh-AddObjectBlock`)
  - `$guide` ← `ldh-CreateItem` (with `Replace`)
  - `POST` (with `CONSTRUCT`, `Substitute`)
  - `ldh-AddXHTMLBlock`
  - `ldh-AddSelect` (with `Substitute`)
  - `ldh-AddView`
  - `ldh-AddObjectBlock`

Operations used: `CONSTRUCT`, `Concat`, `Filter`, `ForEach`, `POST`, `Replace`, `ResolveURI`, `SELECT`, `Str`, `Substitute`, `Value`, `Variable`, `ldh-AddObjectBlock`, `ldh-AddSelect`, `ldh-AddView`, `ldh-AddXHTMLBlock`, `ldh-CreateContainer`, `ldh-CreateItem`.

## Result

From a run on 2026-10-21 against LinkedDataHub ee5905b20 at `https://localhost:4443/`, in 13.7 s. Counts and names come from the live sources and may differ on another day; the shape should not.

8 documents under `https://localhost:4443/unesco-domain-guides/`:

| Document | Title | Content blocks, in order | Other resources | Triples |
|---|---|---|---|---|
| `(container)` | UNESCO Thesaurus domain guides | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | — | 9 |
| `domain1/` | Education | 1. text: “The subject areas of the UNESCO Thesaurus domain Education .”<br>2. `#areas` | 1 sp:Select, 14 skos:Collection, 1 ldh:View | 62 |
| `domain2/` | Science | 1. text: “The subject areas of the UNESCO Thesaurus domain Science .”<br>2. `#areas` | 1 sp:Select, 17 skos:Collection, 1 ldh:View | 71 |
| `domain3/` | Culture | 1. text: “The subject areas of the UNESCO Thesaurus domain Culture .”<br>2. `#areas` | 1 sp:Select, 13 skos:Collection, 1 ldh:View | 59 |
| `domain4/` | Social and human sciences | 1. text: “The subject areas of the UNESCO Thesaurus domain Social and human sciences .”<br>2. `#areas` | 1 sp:Select, 9 skos:Collection, 1 ldh:View | 47 |
| `domain5/` | Information and communication | 1. text: “The subject areas of the UNESCO Thesaurus domain Information and communication .”<br>2. `#areas` | 1 sp:Select, 9 skos:Collection, 1 ldh:View | 47 |
| `domain6/` | Politics, law and economics | 1. text: “The subject areas of the UNESCO Thesaurus domain Politics, law and economics .”<br>2. `#areas` | 1 sp:Select, 17 skos:Collection, 1 ldh:View | 71 |
| `domain7/` | Countries and country groupings | 1. text: “The subject areas of the UNESCO Thesaurus domain Countries and country groupings .”<br>2. `#areas` | 1 sp:Select, 9 skos:Collection, 1 ldh:View | 47 |

Key data ([`result.rq`](result.rq)):

| guide | subjectAreas | forExample |
|---|---|---|
| Countries and country groupings | 9 | Economic groupings |
| Culture | 13 | Languages |
| Education | 14 | Educational administration |
| Information and communication | 9 | Information technology (hardware) |
| Politics, law and economics | 17 | International relations |
| Science | 17 | Pollution, disasters and safety |
| Social and human sciences | 9 | Social problems |

## Checks

After the run, these hold on the instance ([`expect/`](expect/)):

- ✅ `every-guide-holds-its-subject-areas`
- ✅ `seven-guides`

## Run it

```bash
uv run python src/web_algebra/main.py --from-json examples/unesco-domain-guides/plan.json \
  --cert_pem_path $CERT_PEM_PATH --cert_password $CERT_PASSWORD
```

or with its checks, cleaning up after itself:

```bash
CERT_PEM_PATH=... CERT_PASSWORD=... uv run pytest -m ldh tests/test_examples.py -k unesco-domain-guides
```
