# northwind-sales-dashboard

## Instruction

> Make a sales dashboard for Northwind Traders (https://northwind-traders.demo.linkeddatahub.com/sparql) at
> https://localhost:4443/northwind-sales-dashboard/overview/: a short introduction, a bar chart of revenue per
> product category, and a table of the ten customers with the highest revenue, both computed live from the
> Northwind orders.

## Plan

[`plan.json`](plan.json).

- `$dashboard` ← `ldh-CreateContainer`
- `$doc` ← `ldh-CreateItem`
- `ldh-AddGenericService`
- `ldh-AddXHTMLBlock`
- `ldh-AddSelect`
- `ldh-AddResultSetChart`
- `ldh-AddObjectBlock`
- `ldh-AddSelect`
- `ldh-AddResultSetChart`
- `ldh-AddObjectBlock`

Operations used: `Concat`, `Filter`, `ResolveURI`, `Value`, `Variable`, `ldh-AddGenericService`, `ldh-AddObjectBlock`, `ldh-AddResultSetChart`, `ldh-AddSelect`, `ldh-AddXHTMLBlock`, `ldh-CreateContainer`, `ldh-CreateItem`.

## Result

From a run on 2026-10-21 against LinkedDataHub ee5905b20 at `https://localhost:4443/`, in 2.0 s. Counts and names come from the live sources and may differ on another day; the shape should not.

2 documents under `https://localhost:4443/northwind-sales-dashboard/`:

| Document | Title | Content blocks, in order | Other resources | Triples |
|---|---|---|---|---|
| `(container)` | Northwind sales | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | — | 9 |
| `overview/` | Sales overview | 1. text: “Sales overview Revenue from all Northwind orders, by product category and by customer. Both charts query the Northwind endpoint each time the page is viewed.”<br>2. `#revenue-chart`<br>3. `#customers-table` | 2 sp:Select, 1 sd:Service, 2 ldh:ResultSetChart | 41 |

## Checks

After the run, these hold on the instance ([`expect/`](expect/)):

- ✅ `intro-then-bar-chart-then-table`

## Run it

```bash
uv run python src/web_algebra/main.py --from-json examples/northwind-sales-dashboard/plan.json \
  --cert_pem_path $CERT_PEM_PATH --cert_password $CERT_PASSWORD
```

or with its checks, cleaning up after itself:

```bash
CERT_PEM_PATH=... CERT_PASSWORD=... uv run pytest -m ldh tests/test_examples.py -k northwind-sales-dashboard
```
