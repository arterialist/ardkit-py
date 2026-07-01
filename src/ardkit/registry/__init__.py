"""ARD registry layer: a thin, spec-shaped wrapper around your own search.

``ardkit`` owns the ARD wire contract (request parsing, filter semantics,
pagination tokens, federation modes, error codes and response shaping). Your
backend owns ranking by implementing :class:`SearchProvider`. A no-dependency
:class:`InMemorySearchProvider` is included for tests and quickstarts.
"""

from .models import (
    ExploreFacetRequest,
    ExploreResponse,
    FacetBucket,
    FacetResult,
    ListResult,
    QueryModel,
    RegistryReferral,
    ScoredEntry,
    SearchPage,
    SearchQuery,
    SearchRequest,
    SearchResponse,
)
from .provider import SearchProvider, facet_entries, filter_entries, score_entry
from .service import RegistryService

__all__ = [
    "QueryModel",
    "SearchQuery",
    "SearchRequest",
    "SearchResponse",
    "RegistryReferral",
    "ScoredEntry",
    "SearchPage",
    "ListResult",
    "ExploreFacetRequest",
    "ExploreResponse",
    "FacetResult",
    "FacetBucket",
    "SearchProvider",
    "RegistryService",
    "filter_entries",
    "facet_entries",
    "score_entry",
]
