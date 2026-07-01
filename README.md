# ardkit (Python)

[![CI](https://github.com/arterialist/ardkit-py/actions/workflows/ci.yaml/badge.svg)](https://github.com/arterialist/ardkit-py/actions/workflows/ci.yaml)
[![PyPI](https://img.shields.io/pypi/v/ardkit-ai.svg)](https://pypi.org/project/ardkit-ai/)
[![Python](https://img.shields.io/pypi/pyversions/ardkit-ai.svg)](https://pypi.org/project/ardkit-ai/)
[![Docs](https://img.shields.io/badge/docs-ardkit-blue.svg)](https://arterialist.github.io/ardkit-py/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Spec: ai-catalog 1.0](https://img.shields.io/badge/ARD%20spec-1.0-success.svg)](https://agenticresourcediscovery.org/spec/)

Plug-and-play [**ARD** (Agentic Resource Discovery)](https://agenticresourcediscovery.org/spec/)
publisher & registry middleware for Python backends.

ARD lets AI clients **discover** your agents, MCP servers and skills before they
invoke them — instead of every tool description being crammed into the model's
context window. `ardkit` turns any **FastAPI / FastMCP / AG2** backend into an ARD
publisher (and, optionally, a search registry) in a few lines.

```bash
pip install "ardkit-ai[fastapi]"
```

## Quickstart — one call

If your app already mounts its MCP server(s), `publish` finds them and exposes the
lot — no manual catalog needed:

```python
from fastapi import FastAPI
from ardkit.integrations.fastapi import publish

app = FastAPI()
app.mount("/mcp/billing", billing_mcp.http_app())  # your FastMCP, as usual

publish(app, host="Acme AI", publisher="acme.com", base_url="https://app.acme.com")
```

`publish` **never mounts anything** — it reads the route table, maps each mounted
FastMCP back to its instance (identity-based, via fastmcp's app state), introspects
its tools into `capabilities`, and builds the correct public URL from `base_url` +
the mount path. Pass `mcps=[billing_mcp, ...]` to expose specific servers
(unmounted instances are ignored), and `introspect=False` to expose *only* those.

That serves:

| Route | What |
| --- | --- |
| `GET /.well-known/ai-catalog.json` | the manifest (`application/json`, `Access-Control-Allow-Origin: *`) |
| `GET /robots.txt` | with an `Agentmap:` directive pointing at the manifest |

### Or build the catalog by hand

```python
from ardkit import Catalog
from ardkit.integrations.fastapi import mount_ard

catalog = Catalog(host="Acme AI", publisher="acme.com", identifier="did:web:acme.com")
catalog.add_mcp_server(
    name="Billing",
    url="https://acme.com/mcp",
    capabilities=["create_invoice", "list_invoices"],
    representative_queries=["create an invoice", "show unpaid invoices"],
)
mount_ard(app, catalog)
```

Validate a manifest any time from Python:

```python
from ardkit.validation import validate_manifest

errors = validate_manifest(catalog.to_dict())   # [] when it conforms to ai-catalog v1.0
```

## Catalog as a cacheable document origin

When discovery is published on an apex host but the catalog's source of truth is a
backend on another host, expose the manifest as a cacheable JSON *document* on the
backend and have the apex consume it (see ardkit-ts `remoteCatalog`):

```python
from ardkit.integrations.fastapi import add_catalog_route

add_catalog_route(app, catalog, path="/api/ard/ai-catalog.json")
```

`add_catalog_route` (and `mount_ard`) emit a weak `ETag` + `Cache-Control` and
answer conditional `If-None-Match` with `304`, so the document is efficiently
cacheable by the apex/edge.

## Auto-derive entries from your frameworks

```python
from ardkit.adapters import from_mcp_server, from_ag2_agent

# Introspect a FastMCP / mcp-SDK server -> mcp-server-card entry (capabilities = tool names)
catalog.add(from_mcp_server(my_mcp_server, url="https://acme.com/mcp", publisher="acme.com"))

# Map an AG2 / AutoGen agent -> a2a-agent-card entry
catalog.add(from_ag2_agent(my_agent, url="https://acme.com/a2a/agent", publisher="acme.com"))
```

## Optional: be a registry (bring your own search)

`ardkit` owns the ARD wire contract (request parsing, filters, pagination,
federation, error codes, response shaping). **You** own ranking by implementing
`SearchProvider` — or use the bundled `InMemorySearchProvider` for tests/demos.

```python
from ardkit.registry import RegistryService
from ardkit.registry.memory import InMemorySearchProvider

service = RegistryService(
    InMemorySearchProvider(catalog.entries),     # swap for your search engine
    source="https://registry.acme.com/ard/",
)
mount_ard(app, catalog, registry=service, registry_prefix="/ard")
# -> POST /ard/search, POST /ard/explore, GET /ard/agents
```

Implement your own backend by satisfying the protocol:

```python
from ardkit.registry import SearchQuery
from ardkit.registry.models import SearchPage, ScoredEntry

class MySearch:                       # SearchProvider (structural typing)
    async def search(self, query: SearchQuery, *, page_size, page_token) -> SearchPage:
        hits = await my_vector_db.query(query.text, filters=query.filter, k=page_size)
        return SearchPage(items=[ScoredEntry(entry=h.card, score=h.score) for h in hits])
```

`explore` and `list_agents` are optional — omit them and the endpoints return
HTTP 501 as the spec allows.

## What's in the box

- **Spec models** (`ardkit.models`) — Pydantic v2, mirroring `ai-catalog.schema.json`
  (URN validation, `url` XOR `data`, `representativeQueries` 2–5, trust manifest).
- **Builder** (`ardkit.Catalog`) — mints URNs, sets media types, dynamic catalogs.
- **Adapters** (`ardkit.adapters`) — FastMCP / mcp-SDK / AG2.
- **FastAPI integration** (`ardkit.integrations.fastapi`) — `publish` (one call, reads
  your mounted MCPs), `mount_ard`, `add_catalog_route`.
- **Registry** (`ardkit.registry`) — BYO-search service + FastAPI router + in-memory provider.
- **Discovery helpers** (`ardkit.discovery`) — robots `Agentmap`, `<link>`, DNS records.
- **Validation** (`ardkit.validation`) — conformance against the vendored JSON Schema.

## Install extras

| Extra | Adds | For |
| --- | --- | --- |
| `validation` | `jsonschema` | `ardkit.validation` |
| `fastapi` | `fastapi`, `starlette` | `mount_ard`, registry router |
| `mcp` | `mcp` | typing-only convenience for MCP adapters |
| `ag2` | `ag2` | typing-only convenience for AG2 adapter |
| `all` | the above | everything |

The adapters duck-type framework objects, so you can use them without the
matching extra installed.

## Development

```bash
uv sync --group testing --group lint
uv run pytest
uv run ruff check src tests && uv run ruff format src tests --check
uv run pyright src/ardkit
```

The ARD schemas under `src/ardkit/schemas/` are vendored from
[`ards-project/ard-spec`](https://github.com/ards-project/ard-spec); refresh them
with `python scripts/vendor_schemas.py`.

## License

Apache-2.0 — matching the ARD specification. See [LICENSE](LICENSE).
