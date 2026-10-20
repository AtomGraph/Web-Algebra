# northwind-category-catalogue

## Instruction

> Build a product catalogue from the Northwind Traders demo (https://northwind-traders.demo.linkeddatahub.com/sparql):
> a container at https://localhost:4443/northwind-category-catalogue/ with one document per product category.
> Each category document shows the category's description, its picture, and a live list of the category's
> products, queried from Northwind when the page is viewed.

## Plan

[`plan.json`](plan.json).

- `$catalogue` ← `ldh-CreateContainer`
- `ldh-AddGenericService`
- `ForEach` (with `SELECT`, `Variable`, `ldh-CreateItem`, `ldh-AddXHTMLBlock`, `ldh-AddObjectBlock`, `ldh-AddSelect`, `Substitute`, `ldh-AddView`)
  - `$item` ← `ldh-CreateItem`
  - `ldh-AddXHTMLBlock`
  - `ldh-AddObjectBlock`
  - `ldh-AddSelect` (with `Substitute`)
  - `ldh-AddView`
  - `ldh-AddObjectBlock`

Operations used: `Concat`, `Filter`, `ForEach`, `ResolveURI`, `SELECT`, `Str`, `Substitute`, `Value`, `Variable`, `ldh-AddGenericService`, `ldh-AddObjectBlock`, `ldh-AddSelect`, `ldh-AddView`, `ldh-AddXHTMLBlock`, `ldh-CreateContainer`, `ldh-CreateItem`.

## Result

From a run on 2026-10-21 against LinkedDataHub ee5905b20 at `https://localhost:4443/`, in 8.3 s. Counts and names come from the live sources and may differ on another day; the shape should not.

9 documents under `https://localhost:4443/northwind-category-catalogue/`:

| Document | Title | Content blocks, in order | Other resources | Triples |
|---|---|---|---|---|
| `(container)` | Northwind product catalogue | 1. <https://w3id.org/atomgraph/linkeddatahub#ChildrenView> | 1 sd:Service | 16 |
| `1/` | Beverages | 1. text: “Soft drinks coffees teas beers and ales”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/ec56b79671b30ecb98316d9b766fba198286b3b6><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |
| `2/` | Condiments | 1. text: “Sweet and savory sauces relishes spreads and seasonings”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/7e9f535a3bf693ec856702856fffd3be5a3df4f1><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |
| `3/` | Confections | 1. text: “Desserts candies and sweet breads”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/e781b6c8e83be3f23aa241416f92447a66dc35e4><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |
| `4/` | Dairy Products | 1. text: “Cheeses”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/ee14378aa9de087150576af322146ba26552d2e1><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |
| `5/` | Grains/Cereals | 1. text: “Breads crackers pasta and cereal”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/8a3112b3c6691588d47028fd3907f45d24f47784><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |
| `6/` | Meat/Poultry | 1. text: “Prepared meats”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/11885d9b63b4fdac96dad23d4974df0d28bb8b26><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |
| `7/` | Produce | 1. text: “Dried fruit and bean curd”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/7c70989e58855ffd8628e0a7d5144a10fd70a1ee><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |
| `8/` | Seafood | 1. text: “Seaweed and fish”<br>2. <https://northwind-traders.demo.linkeddatahub.com/uploads/778dd323b4e1923b8e0c0166b64913fb255b97a8><br>3. `#products` | 1 sp:Select, 1 ldh:View | 24 |

## Checks

After the run, these hold on the instance ([`expect/`](expect/)):

- ✅ `eight-categories`
- ✅ `every-category-shows-text-picture-products`

## Run it

With `CERT_PEM_PATH` and `CERT_PASSWORD` set to the LinkedDataHub owner certificate and its password:

```bash
uv run web-algebra --from-json examples/northwind-category-catalogue/plan.json
```

or with its checks, cleaning up after itself:

```bash
uv run pytest -m ldh tests/test_examples.py -k northwind-category-catalogue
```
