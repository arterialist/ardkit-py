"""Request/response models for the ARD registry REST API.

Mirrors ``spec/schemas/ard.openapi.yaml`` (vendored). Used by
:class:`~ardkit.registry.service.RegistryService` to parse requests and shape
responses; providers work with the plain :class:`SearchQuery` /
:class:`ScoredEntry` types.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models import CatalogEntry

FilterValue = str | list[str]
Federation = Literal["auto", "referrals", "none"]


class QueryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str | None = None
    filter: dict[str, FilterValue] = Field(default_factory=dict)


class SearchQueryModel(BaseModel):
    """Like :class:`QueryModel` but ``text`` is required (per ``POST /search``)."""

    model_config = ConfigDict(extra="forbid")
    text: str
    filter: dict[str, FilterValue] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: SearchQueryModel
    federation: Federation = "auto"
    page_size: Annotated[int, Field(alias="pageSize", ge=1, le=100)] = 10
    page_token: str | None = Field(default=None, alias="pageToken")


class ExploreFacetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    limit: int = 20
    min_count: int = Field(default=1, alias="minCount")


class _ExploreResultType(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facets: list[ExploreFacetRequest]


class ExploreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: QueryModel | None = None
    result_type: _ExploreResultType = Field(alias="resultType")


# --- internal provider-facing types ---------------------------------------


@dataclass(slots=True)
class SearchQuery:
    """Normalised query handed to a :class:`SearchProvider`."""

    text: str
    filter: dict[str, list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class ScoredEntry:
    """A catalog entry plus its 0–100 relevance score."""

    entry: CatalogEntry | dict[str, Any]
    score: int


@dataclass(slots=True)
class SearchPage:
    """A page of scored results returned by a provider."""

    items: list[ScoredEntry]
    next_page_token: str | None = None


@dataclass(slots=True)
class ListResult:
    """Deterministic listing result for ``GET /agents``."""

    items: Sequence[CatalogEntry | dict[str, Any]]
    total: int | None = None
    next_page_token: str | None = None


@dataclass(slots=True)
class FacetBucket:
    value: str
    count: int


@dataclass(slots=True)
class FacetResult:
    buckets: list[FacetBucket]
    other_count: int = 0


# --- wire response shapes (for typing/help; service emits plain dicts) -----


class RegistryReferral(BaseModel):
    identifier: str
    display_name: str = Field(serialization_alias="displayName")
    type: str
    url: str


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]
    referrals: list[dict[str, Any]] | None = None
    page_token: str | None = Field(default=None, serialization_alias="pageToken")


class ExploreResponse(BaseModel):
    result_type: Literal["facets"] = Field(default="facets", serialization_alias="resultType")
    facets: dict[str, Any]


__all__ = [
    "FilterValue",
    "Federation",
    "QueryModel",
    "SearchQueryModel",
    "SearchRequest",
    "ExploreFacetRequest",
    "ExploreRequest",
    "SearchQuery",
    "ScoredEntry",
    "SearchPage",
    "ListResult",
    "FacetBucket",
    "FacetResult",
    "RegistryReferral",
    "SearchResponse",
    "ExploreResponse",
]
