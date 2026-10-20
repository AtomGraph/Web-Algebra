# northwind-data-quality

## Instruction

> Audit the contact data of the companies in Northwind Traders (https://northwind-traders.demo.linkeddatahub.com/sparql)
> and publish the result at https://localhost:4443/northwind-data-quality/customer-contacts/: say how many companies
> there are and how many have no telephone number or no contact point, and list the companies without a contact point.

## Plan

[`plan.json`](plan.json).

- `$audit` ← `ldh-CreateContainer`
- `$doc` ← `ldh-CreateItem`
- `$stats` ← `SELECT`
- `ldh-AddXHTMLBlock`
- `ldh-AddGenericService`
- `ldh-AddSelect`
- `ldh-AddView`
- `ldh-AddObjectBlock`

Operations used: `Concat`, `Filter`, `ResolveURI`, `SELECT`, `Str`, `Value`, `Variable`, `ldh-AddGenericService`, `ldh-AddObjectBlock`, `ldh-AddSelect`, `ldh-AddView`, `ldh-AddXHTMLBlock`, `ldh-CreateContainer`, `ldh-CreateItem`.

## Result

From a run on 2026-10-21 against LinkedDataHub ee5905b20 at `https://localhost:4443/`, in 2.0 s. Counts and names come from the live sources and may differ on another day; the shape should not.

2 documents under `https://localhost:4443/northwind-data-quality/`:

| Document | Title | Content blocks, in order | Other resources | Triples |
|---|---|---|---|---|
| `(container)` | Northwind data quality | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | — | 9 |
| `customer-contacts/` | Customer contact data | 1. text: “Contact data audit Of 123 companies, 120 have no telephone number and 3 have no contact point.”<br>2. `#missing-contact-list` | 1 sp:Select, 1 sd:Service, 1 ldh:View | 26 |

## Checks

After the run, these hold on the instance ([`expect/`](expect/)):

- ✅ `report-lists-the-offenders`
- ✅ `report-states-the-counts`

## Run it

With `CERT_PEM_PATH` and `CERT_PASSWORD` set to the LinkedDataHub owner certificate and its password:

```bash
uv run web-algebra --from-json examples/northwind-data-quality/plan.json
```

or with its checks, cleaning up after itself:

```bash
uv run pytest -m ldh tests/test_examples.py -k northwind-data-quality
```
