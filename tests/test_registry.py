import pytest

from ardkit import Catalog
from ardkit.errors import InvalidArgument, NotImplementedByServer
from ardkit.registry import RegistryService
from ardkit.registry.memory import InMemorySearchProvider


def _catalog():
    cat = Catalog(host="Acme AI", publisher="acme.com")
    cat.add_mcp_server(
        name="Weather",
        url="https://acme.com/mcp/weather",
        capabilities=["WeatherTool", "ForecastTool"],
        tags=["weather"],
        representative_queries=["current weather in Chicago", "5 day forecast Seattle"],
    )
    cat.add_a2a_agent(
        name="Billing Agent",
        url="https://acme.com/a2a/billing",
        tags=["finance"],
        representative_queries=["create an invoice", "show unpaid invoices"],
    )
    return cat


def _service():
    provider = InMemorySearchProvider(_catalog().entries)
    return RegistryService(provider, source="https://registry.acme.com/ard/")


async def test_search_ranks_and_stamps_source():
    svc = _service()
    resp = await svc.search({"query": {"text": "weather forecast"}})
    assert resp["results"]
    top = resp["results"][0]
    assert "weather" in top["displayName"].lower()
    assert top["source"] == "https://registry.acme.com/ard/"
    assert 0 <= top["score"] <= 100


async def test_search_filter_by_type_and_tag():
    svc = _service()
    resp = await svc.search(
        {
            "query": {
                "text": "anything",
                "filter": {"type": ["application/a2a-agent-card+json"], "tags": ["finance"]},
            }
        }
    )
    assert len(resp["results"]) == 1
    assert resp["results"][0]["type"] == "application/a2a-agent-card+json"


async def test_search_pagination():
    svc = _service()
    page1 = await svc.search({"query": {"text": "a"}, "pageSize": 1})
    assert len(page1["results"]) == 1
    assert "pageToken" in page1
    page2 = await svc.search(
        {"query": {"text": "a"}, "pageSize": 1, "pageToken": page1["pageToken"]}
    )
    assert len(page2["results"]) == 1
    assert page1["results"][0]["identifier"] != page2["results"][0]["identifier"]


async def test_referrals_mode_includes_referrals():
    provider = InMemorySearchProvider(_catalog().entries)
    svc = RegistryService(
        provider,
        source="https://registry.acme.com/ard/",
        referrals=[
            {
                "identifier": "urn:air:nlweb.ai:registry:public",
                "displayName": "Public Finder",
                "type": "application/ai-registry+json",
                "url": "https://finder.nlweb.ai/search",
            }
        ],
    )
    resp = await svc.search({"query": {"text": "weather"}, "federation": "referrals"})
    assert resp["referrals"][0]["url"] == "https://finder.nlweb.ai/search"
    none = await svc.search({"query": {"text": "weather"}, "federation": "none"})
    assert "referrals" not in none


async def test_search_requires_text():
    svc = _service()
    with pytest.raises(InvalidArgument):
        await svc.search({"query": {"filter": {"type": ["x"]}}})


async def test_explore_facets():
    svc = _service()
    resp = await svc.explore({"resultType": {"facets": [{"field": "type"}]}})
    assert resp["resultType"] == "facets"
    buckets = resp["facets"]["type"]["buckets"]
    values = {b["value"] for b in buckets}
    assert "application/mcp-server-card+json" in values


async def test_list_agents_cel_filter():
    svc = _service()
    # CEL: equality + membership against entry fields.
    resp = await svc.list_agents(
        filter='type == "application/a2a-agent-card+json" && "finance" in tags'
    )
    assert resp["total"] == 1
    assert resp["items"][0]["type"] == "application/a2a-agent-card+json"


async def test_list_agents_invalid_cel_filter_is_400():
    from ardkit.errors import InvalidArgument

    svc = _service()
    with pytest.raises(InvalidArgument):
        await svc.list_agents(filter="type = = =")


async def test_optional_endpoints_501_when_unsupported():
    class Bare:
        async def search(self, query, *, page_size, page_token):
            from ardkit.registry.models import SearchPage

            return SearchPage(items=[])

    svc = RegistryService(Bare(), source="https://r.acme.com/")
    with pytest.raises(NotImplementedByServer):
        await svc.explore({"resultType": {"facets": [{"field": "type"}]}})
    with pytest.raises(NotImplementedByServer):
        await svc.list_agents()
