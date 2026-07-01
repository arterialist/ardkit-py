"""Minimal ARD publisher + registry on FastAPI.

Run:
    uv run --with 'ardkit-ai[fastapi]' uvicorn examples.fastapi_min.app:app --reload

Then:
    curl -s localhost:8000/.well-known/ai-catalog.json | jq
    curl -s localhost:8000/robots.txt
    curl -s localhost:8000/ard/search -d '{"query":{"text":"weather"}}' | jq
"""

from __future__ import annotations

from fastapi import FastAPI

from ardkit import Catalog
from ardkit.integrations.fastapi import mount_ard
from ardkit.registry import RegistryService
from ardkit.registry.memory import InMemorySearchProvider

app = FastAPI(title="ardkit example")

catalog = Catalog(host="Acme AI", publisher="acme.com", identifier="did:web:acme.com")
catalog.add_mcp_server(
    name="Weather",
    url="https://acme.com/mcp/weather",
    capabilities=["WeatherTool", "ForecastTool"],
    tags=["weather"],
    description="Live weather + forecasts over MCP.",
    representative_queries=["current weather in Chicago", "5-day forecast for Seattle"],
)
catalog.add_a2a_agent(
    name="Billing Agent",
    url="https://acme.com/a2a/billing",
    tags=["finance"],
    description="Creates and reconciles invoices.",
    representative_queries=["create an invoice", "show unpaid invoices"],
)

# Optional registry over the same entries (swap InMemory for your search engine).
registry = RegistryService(
    InMemorySearchProvider(catalog.entries),
    source="http://localhost:8000/ard/",
    referrals=[
        {
            "identifier": "urn:air:nlweb.ai:registry:public",
            "displayName": "Public Agent Finder",
            "type": "application/ai-registry+json",
            "url": "https://finder.nlweb.ai/search",
        }
    ],
)

mount_ard(app, catalog, registry=registry, registry_prefix="/ard")
