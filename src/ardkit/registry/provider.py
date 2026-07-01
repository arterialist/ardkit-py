"""The ``SearchProvider`` contract and reusable matching/faceting helpers.

A host implements :class:`SearchProvider` (only :meth:`~SearchProvider.search`
is mandatory). The helper functions — :func:`filter_entries`, :func:`score_entry`
and :func:`facet_entries` — implement the ARD filter/facet semantics so a
provider can delegate the boilerplate and focus on ranking (or, like
:class:`~ardkit.registry.memory.InMemorySearchProvider`, lean on them entirely).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from ..models import CatalogEntry
from .models import (
    FacetBucket,
    FacetResult,
    ListResult,
    ScoredEntry,
    SearchPage,
    SearchQuery,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@runtime_checkable
class SearchProvider(Protocol):
    """Bring-your-own-search backend behind the ARD registry endpoints."""

    async def search(
        self, query: SearchQuery, *, page_size: int, page_token: str | None
    ) -> SearchPage:
        """Return a ranked, paginated page of results for ``query``."""
        ...

    # Optional. Omit (or raise NotImplementedError) to return HTTP 501.
    async def explore(
        self, query: SearchQuery, fields: list[tuple[str, int, int]]
    ) -> dict[str, FacetResult]:  # pragma: no cover - optional
        """Aggregate facets. ``fields`` is ``[(field, limit, min_count), ...]``."""
        raise NotImplementedError

    async def list_agents(
        self,
        *,
        filter: str | None,
        order_by: str | None,
        page_size: int,
        page_token: str | None,
    ) -> ListResult:  # pragma: no cover - optional
        """Deterministic listing for ``GET /agents``."""
        raise NotImplementedError


# --------------------------------------------------------------------------
# Reusable semantics


def as_dict(entry: CatalogEntry | dict[str, Any]) -> dict[str, Any]:
    """Normalise an entry to a spec-shaped dict."""
    if isinstance(entry, CatalogEntry):
        return entry.model_dump(mode="json", by_alias=True, exclude_none=True)
    return entry


def extract_path(obj: Any, path: str) -> list[str]:
    """Collect scalar leaves at a dot-separated ``path``, descending into lists."""
    current: list[Any] = [obj]
    for segment in path.split("."):
        nxt: list[Any] = []
        for item in current:
            if isinstance(item, dict) and segment in item:
                value = item[segment]
                nxt.extend(value if isinstance(value, list) else [value])
            elif isinstance(item, list):
                for sub in item:
                    if isinstance(sub, dict) and segment in sub:
                        value = sub[segment]
                        nxt.extend(value if isinstance(value, list) else [value])
        current = nxt
    return [str(v) for v in current if v is not None and not isinstance(v, (dict, list))]


def entry_matches(entry_dict: dict[str, Any], filters: dict[str, list[str]]) -> bool:
    """ARD filter semantics: OR within a key, AND across keys."""
    for key, wanted in filters.items():
        if not wanted:
            continue
        found = set(extract_path(entry_dict, key))
        if not found.intersection(wanted):
            return False
    return True


def filter_entries(
    entries: Sequence[CatalogEntry | dict[str, Any]], filters: dict[str, list[str]]
) -> list[dict[str, Any]]:
    """Return the entries (as dicts) matching every filter key."""
    dicts = [as_dict(e) for e in entries]
    if not filters:
        return dicts
    return [d for d in dicts if entry_matches(d, filters)]


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def score_entry(text: str, entry: CatalogEntry | dict[str, Any]) -> int:
    """A naive 0–100 lexical relevance score (token overlap, field-weighted)."""
    d = as_dict(entry)
    query_tokens = _tokens(text)
    if not query_tokens:
        return 0
    weighted: list[tuple[float, str]] = [
        (3.0, d.get("displayName", "")),
        (2.0, " ".join(d.get("representativeQueries", []) or [])),
        (2.0, " ".join(d.get("capabilities", []) or [])),
        (1.5, " ".join(d.get("tags", []) or [])),
        (1.0, d.get("description", "")),
    ]
    score = 0.0
    max_score = 0.0
    for weight, value in weighted:
        max_score += weight
        field_tokens = _tokens(value)
        if field_tokens:
            overlap = len(query_tokens & field_tokens) / len(query_tokens)
            score += weight * overlap
    if max_score == 0:
        return 0
    return max(0, min(100, round(100 * score / max_score)))


def facet_entries(
    entries: Sequence[CatalogEntry | dict[str, Any]],
    field: str,
    *,
    limit: int = 20,
    min_count: int = 1,
) -> FacetResult:
    """Aggregate value counts at ``field`` into ranked buckets."""
    counter: Counter[str] = Counter()
    for e in entries:
        for value in extract_path(as_dict(e), field):
            counter[value] += 1
    ranked = [(v, c) for v, c in counter.most_common() if c >= min_count]
    kept = ranked[:limit]
    other = sum(c for _, c in ranked[limit:]) + sum(c for v, c in counter.items() if c < min_count)
    return FacetResult(
        buckets=[FacetBucket(value=v, count=c) for v, c in kept],
        other_count=other,
    )


def score_and_sort(
    text: str, entries: Sequence[CatalogEntry | dict[str, Any]]
) -> list[ScoredEntry]:
    """Score every entry and return them sorted by descending score."""
    scored = [ScoredEntry(entry=as_dict(e), score=score_entry(text, e)) for e in entries]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


__all__ = [
    "SearchProvider",
    "as_dict",
    "extract_path",
    "entry_matches",
    "filter_entries",
    "score_entry",
    "facet_entries",
    "score_and_sort",
]
