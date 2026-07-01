# ardkit

Plug-and-play **ARD (Agentic Resource Discovery)** publisher & registry
middleware for Python backends (FastAPI / FastMCP / AG2).

[ARD](https://agenticresourcediscovery.org/spec/) lets AI clients *discover* your
agents, MCP servers and skills before invoking them — instead of stuffing every
tool description into the model's context window. `ardkit` turns your backend into
an ARD **publisher** (and optionally a search **registry**) in a few lines.

```bash
pip install "ardkit-ai[fastapi]"   # import name: ardkit
```

```python
from fastapi import FastAPI
from ardkit import Catalog
from ardkit.integrations.fastapi import mount_ard

app = FastAPI()
catalog = Catalog(host="Acme AI", publisher="acme.com", identifier="did:web:acme.com")
catalog.add_mcp_server(
    name="Billing", url="https://acme.com/mcp",
    capabilities=["create_invoice"],
    representative_queries=["create an invoice", "show unpaid invoices"],
)
mount_ard(app, catalog)
```

- **[Quickstart](quickstart.md)** — publish a catalog and add discovery hints.
- **[Adapters](adapters.md)** — auto-derive entries from FastMCP / mcp-SDK / AG2.
- **[Registry](registry.md)** — expose ARD search over your own engine.
- **[Concepts](concepts.md)** — how ardkit maps onto the ARD spec.
