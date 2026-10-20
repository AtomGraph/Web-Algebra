# city-profiles

## Instruction

> Create profile pages for Copenhagen, Aarhus and Odense under https://localhost:4443/city-profiles/ from their
> DBpedia descriptions: the English name, population (the official total, or failing that the urban population), coordinates and picture. Each page shows the picture and the
> city on a map. Fetch each city's own DBpedia document rather than querying the DBpedia endpoint.

## Plan

[`plan.json`](plan.json).

- `$cities` ← `ldh-CreateContainer`
- `ForEach` (with `Variable`, `EncodeForURI`, `GET`, `ldh-CreateItem`, `POST`, `CONSTRUCT`, `Substitute`, `ldh-AddObjectBlock`, `SELECT`, `ldh-AddSelect`, `ldh-AddView`)
  - `$city` ← `EncodeForURI`
  - `$description` ← `GET`
  - `$page` ← `ldh-CreateItem` (with `EncodeForURI`)
  - `POST` (with `CONSTRUCT`, `Substitute`)
  - `ldh-AddObjectBlock` (with `SELECT`, `Substitute`)
  - `ldh-AddSelect` (with `Substitute`)
  - `ldh-AddView`
  - `ldh-AddObjectBlock`

Operations used: `CONSTRUCT`, `Current`, `EncodeForURI`, `Filter`, `ForEach`, `GET`, `POST`, `ResolveURI`, `SELECT`, `Substitute`, `Value`, `Variable`, `ldh-AddObjectBlock`, `ldh-AddSelect`, `ldh-AddView`, `ldh-CreateContainer`, `ldh-CreateItem`.

## Result

From a run on 2026-10-21 against LinkedDataHub ee5905b20 at `https://localhost:4443/`, in 4.3 s. Counts and names come from the live sources and may differ on another day; the shape should not.

4 documents under `https://localhost:4443/city-profiles/`:

| Document | Title | Content blocks, in order | Other resources | Triples |
|---|---|---|---|---|
| `(container)` | Danish cities | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | — | 9 |
| `Aarhus/` | Aarhus | 1. <http://commons.wikimedia.org/wiki/Special:FilePath/Drone_photo_of_Dokk1_in_Aarhus,_Denmark.jpg?width=300><br>2. `#map` | 1 sp:Select, 1 ldh:View | 25 |
| `Copenhagen/` | Copenhagen | 1. <http://commons.wikimedia.org/wiki/Special:FilePath/Christiansborg_fra_Nikolaj_Kirken.jpg?width=300><br>2. `#map` | 1 sp:Select, 1 ldh:View | 25 |
| `Odense/` | Odense | 1. <http://commons.wikimedia.org/wiki/Special:FilePath/Odense_-_Sankt_Knuds_kirke_2005-07-16.jpeg?width=300><br>2. `#map` | 1 sp:Select, 1 ldh:View | 25 |

Key data ([`result.rq`](result.rq)):

| city | population | lat | long |
|---|---|---|---|
| Aarhus | 301049 | 56.15 | 10.216666 |
| Copenhagen | 667099 | 55.67611 | 12.568334 |
| Odense | 185480 | 55.395832 | 10.388611 |

## Checks

After the run, these hold on the instance ([`expect/`](expect/)):

- ✅ `every-page-shows-picture-and-map`
- ✅ `three-cities-with-coordinates`

## Run it

```bash
uv run python src/web_algebra/main.py --from-json examples/city-profiles/plan.json \
  --cert_pem_path $CERT_PEM_PATH --cert_password $CERT_PASSWORD
```

or with its checks, cleaning up after itself:

```bash
CERT_PEM_PATH=... CERT_PASSWORD=... uv run pytest -m ldh tests/test_examples.py -k city-profiles
```
