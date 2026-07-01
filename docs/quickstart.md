# Quickstart

## 1. Build a catalog

```python
from ardkit import Catalog

catalog = Catalog(host="Acme AI", publisher="acme.com", identifier="did:web:acme.com")
catalog.add_mcp_server(
    name="Billing",
    url="https://acme.com/mcp",
    capabilities=["create_invoice", "list_invoices"],
    representative_queries=["create an invoice", "show unpaid invoices"],
)
catalog.add_a2a_agent(
    name="Support Agent",
    url="https://acme.com/a2a/support",
    representative_queries=["open a support ticket", "check ticket status"],
)
```

URNs are minted from `publisher` automatically
(`urn:air:acme.com:mcp:billing`). Pass `identifier=` to set one explicitly.

## 2. Serve it on FastAPI

```python
from fastapi import FastAPI
from ardkit.integrations.fastapi import mount_ard

app = FastAPI()
mount_ard(app, catalog)
```

This registers `GET /.well-known/ai-catalog.json` (with
`Content-Type: application/json` and `Access-Control-Allow-Origin: *`) and a
`GET /robots.txt` carrying an `Agentmap:` directive.

!!! tip "Dynamic catalogs"
    Pass a zero-arg callable (sync or async) instead of a `Catalog` to rebuild
    the manifest per request from your database:
    `mount_ard(app, lambda: build_catalog_from_db())`.

## 3. Validate

```python
from ardkit.validation import validate_manifest
assert validate_manifest(catalog.to_manifest()) == []
```

## Other discovery hints

```python
from ardkit.discovery import link_tag, dns_records

link_tag("https://acme.com/.well-known/ai-catalog.json")
dns_records("acme.com", catalog_url="https://acme.com/.well-known/ai-catalog.json")
```
