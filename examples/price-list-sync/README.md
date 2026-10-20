# price-list-sync

## Instruction

> The product documents under https://localhost:4443/price-list-sync/products/ must carry the prices of the master
> price list at https://localhost:4443/price-list-sync/master/. Update every product's price from the master list,
> matching products by SKU. Running the update again must change nothing.

## Plan

[`plan.json`](plan.json) runs after [`setup.json`](setup.json), which creates the starting state.

- `$master` ← `GET`
- `ForEach` (with `ldh-List`, `Variable`, `GET`, `SELECT`, `Substitute`, `PATCH`)
  - `$product` ← `GET`
  - `$sku` ← `SELECT`
  - `$price` ← `SELECT` (with `Substitute`)
  - `PATCH` (with `Substitute`)

Operations used: `Filter`, `ForEach`, `GET`, `PATCH`, `POST`, `SELECT`, `Substitute`, `Value`, `Variable`, `ldh-CreateContainer`, `ldh-CreateItem`, `ldh-List`.

## Result

From a run on 2026-10-21 against LinkedDataHub ee5905b20 at `https://localhost:4443/`, in 4.0 s. Counts and names come from the live sources and may differ on another day; the shape should not.

6 documents under `https://localhost:4443/price-list-sync/`:

| Document | Title | Content blocks, in order | Other resources | Triples |
|---|---|---|---|---|
| `(container)` | Price list | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | — | 9 |
| `master/` | Master price list | — | — | 13 |
| `products/` | Products | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | — | 9 |
| `products/chai/` | Chai | — | 1 schema:Product | 11 |
| `products/ikura/` | Ikura | — | 1 schema:Product | 11 |
| `products/queso-cabrales/` | Queso Cabrales | — | 1 schema:Product | 11 |

Key data ([`result.rq`](result.rq)):

| product | sku | price |
|---|---|---|
| Chai | NW-1 | 19.5 |
| Ikura | NW-10 | 31.0 |
| Queso Cabrales | NW-11 | 22.75 |

## Checks

After the run, these hold on the instance ([`expect/`](expect/)):

- ✅ `one-price-per-product`
- ✅ `prices-follow-the-master-list`

## Run it

With `CERT_PEM_PATH` and `CERT_PASSWORD` set to the LinkedDataHub owner certificate and its password:

```bash
uv run web-algebra --from-json examples/price-list-sync/setup.json
uv run web-algebra --from-json examples/price-list-sync/plan.json
```

or with its checks, cleaning up after itself:

```bash
uv run pytest -m ldh tests/test_examples.py -k price-list-sync
```
