import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from ardkit import Catalog  # noqa: E402
from ardkit.integrations.fastapi import mount_ard  # noqa: E402
from ardkit.registry import RegistryService  # noqa: E402
from ardkit.registry.memory import InMemorySearchProvider  # noqa: E402
from ardkit.validation import validate_manifest  # noqa: E402


def _catalog():
    cat = Catalog(host="Acme AI", publisher="acme.com", identifier="did:web:acme.com")
    cat.add_mcp_server(
        name="Weather",
        url="https://acme.com/mcp/weather",
        capabilities=["WeatherTool"],
        tags=["weather"],
        representative_queries=["weather in Chicago", "forecast Seattle"],
    )
    return cat


def test_well_known_served_with_headers():
    app = FastAPI()
    mount_ard(app, _catalog())
    client = TestClient(app)
    resp = client.get("/.well-known/ai-catalog.json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.headers["access-control-allow-origin"] == "*"
    assert "stale-while-revalidate" in resp.headers["cache-control"]
    assert resp.headers["etag"]
    body = resp.json()
    assert validate_manifest(body) == []


def test_conditional_request_returns_304():
    app = FastAPI()
    mount_ard(app, _catalog())
    client = TestClient(app)
    first = client.get("/.well-known/ai-catalog.json")
    etag = first.headers["etag"]
    second = client.get("/.well-known/ai-catalog.json", headers={"If-None-Match": etag})
    assert second.status_code == 304


def test_catalog_document_origin_route():
    # Backend-origin usage: serve the catalog at a custom path, no robots.
    from ardkit.integrations.fastapi import add_catalog_route

    app = FastAPI()
    add_catalog_route(app, _catalog(), path="/api/ard/ai-catalog.json")
    client = TestClient(app)
    resp = client.get("/api/ard/ai-catalog.json")
    assert resp.status_code == 200
    assert validate_manifest(resp.json()) == []
    assert client.get("/robots.txt").status_code == 404  # no robots on the origin


class _Tool:
    def __init__(self, name):
        self.name = name


class _ToolMgr:
    """Mimics fastmcp v2 ToolManager: sync ``_tools`` dict, async ``get_tools``."""

    def __init__(self, *names):
        self._tools = {n: _Tool(n) for n in names}

    async def get_tools(self):
        return self._tools


class _FastMCP:
    def __init__(self, name, *tools):
        self.name = name
        self._tool_manager = _ToolMgr(*tools)


def _mount_fastmcp(app, mount_path, server, inner_path="/mcp"):
    """Mount a FastMCP-like server the way fastmcp's http_app() exposes it:
    a sub-app carrying ``state.fastmcp_server`` and ``state.path``."""
    from fastapi import FastAPI as _Sub

    sub = _Sub()
    sub.state.fastmcp_server = server
    sub.state.path = inner_path
    app.mount(mount_path, sub)
    return sub


def test_publish_introspects_mounted_mcp():
    from ardkit.integrations.fastapi import publish

    app = FastAPI()
    _mount_fastmcp(app, "/mcp/billing", _FastMCP("Billing", "a", "b"))

    cat = publish(app, host="Acme AI", publisher="acme.com", base_url="https://app.acme.com")
    client = TestClient(app)
    body = client.get("/.well-known/ai-catalog.json").json()
    assert validate_manifest(body) == []
    entry = body["entries"][0]
    # mount path joined with the streamable sub-path
    assert entry["url"] == "https://app.acme.com/mcp/billing/mcp"
    assert entry["capabilities"] == ["a", "b"]

    # Returned catalog is live: later additions show up on the next request.
    cat.add_a2a_agent(name="Helper", url="https://acme.com/a2a", representative_queries=["x", "y"])
    assert len(client.get("/.well-known/ai-catalog.json").json()["entries"]) == 2


def test_publish_explicit_list_ignores_unmounted_and_disables_introspect():
    from ardkit.integrations.fastapi import publish

    app = FastAPI()
    mounted = _FastMCP("Mounted", "x")
    unmounted = _FastMCP("Unmounted", "y")
    other = _FastMCP("Other", "z")
    _mount_fastmcp(app, "/mcp/mounted", mounted)
    _mount_fastmcp(app, "/mcp/other", other)  # would appear only if introspecting

    publish(
        app,
        host="Acme AI",
        publisher="acme.com",
        base_url="https://acme.com",
        mcps=[mounted, unmounted],  # unmounted is silently ignored
        introspect=False,  # so /mcp/other is NOT exposed
    )
    body = TestClient(app).get("/.well-known/ai-catalog.json").json()
    assert validate_manifest(body) == []
    urls = [e["url"] for e in body["entries"]]
    assert urls == ["https://acme.com/mcp/mounted/mcp"]


def test_robots_has_agentmap():
    app = FastAPI()
    mount_ard(app, _catalog())
    client = TestClient(app)
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "Agentmap:" in resp.text
    assert "/.well-known/ai-catalog.json" in resp.text


def test_dynamic_callable_source():
    app = FastAPI()
    mount_ard(app, lambda: _catalog().to_dict())
    client = TestClient(app)
    assert client.get("/.well-known/ai-catalog.json").status_code == 200


def test_registry_endpoints():
    app = FastAPI()
    provider = InMemorySearchProvider(_catalog().entries)
    service = RegistryService(provider, source="https://registry.acme.com/ard/")
    mount_ard(app, _catalog(), registry=service, registry_prefix="/ard")
    client = TestClient(app)

    resp = client.post("/ard/search", json={"query": {"text": "weather"}})
    assert resp.status_code == 200
    assert resp.json()["results"][0]["source"] == "https://registry.acme.com/ard/"

    bad = client.post("/ard/search", json={"query": {}})
    assert bad.status_code == 400
    assert bad.json()["errorCode"] == "INVALID_ARGUMENT"

    explore = client.post("/ard/explore", json={"resultType": {"facets": [{"field": "type"}]}})
    assert explore.status_code == 200
    assert explore.json()["resultType"] == "facets"
