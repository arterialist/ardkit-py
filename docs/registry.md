# Registry (bring your own search)

ardkit's registry layer is a **thin protocol wrapper**: it owns the ARD wire
contract — request parsing, filter semantics (OR within a key, AND across keys),
opaque pagination tokens, federation modes, error codes and response shaping —
and delegates ranking to *your* search backend.

## The contract

```python
from ardkit.registry import SearchQuery
from ardkit.registry.models import SearchPage, ScoredEntry, FacetResult, ListResult

class SearchProvider:
    async def search(self, query: SearchQuery, *, page_size: int, page_token: str | None) -> SearchPage: ...

    # optional — omit to return HTTP 501
    async def explore(self, query: SearchQuery, fields: list[tuple[str, int, int]]) -> dict[str, FacetResult]: ...
    async def list_agents(self, *, filter, order_by, page_size, page_token) -> ListResult: ...
```

Only `search` is required. `SearchProvider` is a structural (`Protocol`) type —
any object with the right methods works.

## Wire it up

```python
from ardkit.registry import RegistryService
from ardkit.integrations.fastapi import mount_ard

service = RegistryService(MySearch(), source="https://registry.acme.com/ard/")
mount_ard(app, catalog, registry=service, registry_prefix="/ard")
```

Endpoints: `POST /ard/search`, `POST /ard/explore`, `GET /ard/agents`.

## Reuse the built-in semantics

Implementing `search` from scratch? The helpers do the spec-defined filtering and
faceting for you, so you only add ranking:

```python
from ardkit.registry.provider import filter_entries, score_and_sort, facet_entries

class MySearch:
    def __init__(self, entries): self.entries = entries
    async def search(self, query, *, page_size, page_token):
        matched = filter_entries(self.entries, query.filter)
        ranked = score_and_sort(query.text, matched)   # or your own scorer
        ...
```

`InMemorySearchProvider` is a complete reference implementation built on these
helpers — good for tests and demos, swap it for a real engine in production.

## Federation & referrals

```python
RegistryService(provider, source="...", referrals=[
    {"identifier": "urn:air:nlweb.ai:registry:public",
     "displayName": "Public Finder",
     "type": "application/ai-registry+json",
     "url": "https://finder.nlweb.ai/search"},
])
```

Referrals are returned in `referrals` (and offered in `auto`) federation modes,
and omitted in `none`.
