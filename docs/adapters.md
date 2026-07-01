# Adapters

Adapters introspect framework objects and return ready-to-add `CatalogEntry`
objects. They **duck-type** the objects, so you don't need the framework's extra
installed to use them.

## MCP servers (FastMCP / mcp SDK)

```python
from ardkit.adapters import from_mcp_server

entry = from_mcp_server(
    my_server,                       # mcp.server.fastmcp.FastMCP or fastmcp.FastMCP
    url="https://acme.com/mcp",
    publisher="acme.com",
    representative_queries=["create an invoice", "list invoices"],
)
catalog.add(entry)
```

`capabilities` defaults to the server's tool names (introspected via the tool
manager). Pass `capabilities=[...]` to override. Produces an
`application/mcp-server-card+json` entry. `from_fastmcp` is an explicit alias.

## AG2 / AutoGen agents

```python
from ardkit.adapters import from_ag2_agent, from_ag2_agents

catalog.add(from_ag2_agent(agent, url="https://acme.com/a2a/agent", publisher="acme.com"))

# Many at once, with a URL per agent:
catalog_entries = from_ag2_agents(
    agents,
    publisher="acme.com",
    url_for=lambda a: f"https://acme.com/a2a/{a.name}",
)
```

`description` falls back to the agent's `description` / `system_message`.
Produces `application/a2a-agent-card+json` entries.
