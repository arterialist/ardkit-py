"""An in-memory ``SearchProvider`` for tests and quickstarts.

Backed by a static list of entries (or a callable returning the current list, so
it can wrap a dynamic catalog). Ranking uses the naive lexical scorer in
:mod:`ardkit.registry.provider`; pagination uses opaque base64 offset tokens; the
``GET /agents`` filter is a CEL expression (``cel-python``). Swap it for your real
search engine in production.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Any

import celpy

from ..errors import InvalidArgument
from ..models import CatalogEntry
from .models import (
    FacetResult,
    ListResult,
    ScoredEntry,
    SearchPage,
    SearchQuery,
)
from .provider import (
    as_dict,
    extract_path,
    facet_entries,
    filter_entries,
    score_and_sort,
)

EntriesSource = (
    list[CatalogEntry | dict[str, Any]] | Callable[[], list[CatalogEntry | dict[str, Any]]]
)


def _encode_token(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _decode_token(token: str | None) -> int:
    if not token:
        return 0
    try:
        return int(base64.urlsafe_b64decode(token.encode()).decode())
    except (ValueError, TypeError):
        raise InvalidArgument(f"invalid pageToken: {token!r}") from None


class InMemorySearchProvider:
    """Lexical search over a fixed (or callable) set of catalog entries."""

    def __init__(self, entries: EntriesSource):
        self._entries = entries

    def _all(self) -> list[CatalogEntry | dict[str, Any]]:
        return list(self._entries() if callable(self._entries) else self._entries)

    async def search(
        self, query: SearchQuery, *, page_size: int, page_token: str | None
    ) -> SearchPage:
        matched = filter_entries(self._all(), query.filter)
        ranked: list[ScoredEntry] = score_and_sort(query.text, matched)
        offset = _decode_token(page_token)
        page = ranked[offset : offset + page_size]
        next_token = _encode_token(offset + page_size) if offset + page_size < len(ranked) else None
        return SearchPage(items=page, next_page_token=next_token)

    async def explore(
        self, query: SearchQuery, fields: list[tuple[str, int, int]]
    ) -> dict[str, FacetResult]:
        matched = filter_entries(self._all(), query.filter)
        if query.text:
            matched = [s.entry for s in score_and_sort(query.text, matched) if s.score > 0]  # type: ignore[misc]
        return {
            field: facet_entries(matched, field, limit=limit, min_count=min_count)
            for field, limit, min_count in fields
        }

    async def list_agents(
        self,
        *,
        filter: str | None,
        order_by: str | None,
        page_size: int,
        page_token: str | None,
    ) -> ListResult:
        items = [as_dict(e) for e in self._all()]
        items = _apply_cel_filter(items, filter)
        items = _apply_order(items, order_by)
        total = len(items)
        offset = _decode_token(page_token)
        page = items[offset : offset + page_size]
        next_token = _encode_token(offset + page_size) if offset + page_size < total else None
        return ListResult(items=page, total=total, next_page_token=next_token)


def _apply_cel_filter(items: list[dict[str, Any]], expr: str | None) -> list[dict[str, Any]]:
    """Filter entries by a CEL expression (e.g. ``type == "..." && "x" in tags``).

    Each entry's top-level fields become CEL variables, so ``metadata.tier``,
    ``"finance" in tags`` and comparisons all work. Entries whose expression
    references an absent field are treated as non-matches rather than errors.
    """
    if not expr:
        return items

    env = celpy.Environment()
    try:
        program = env.program(env.compile(expr))
    except celpy.CELParseError as exc:
        raise InvalidArgument(f"invalid filter expression: {expr!r}") from exc

    out: list[dict[str, Any]] = []
    for d in items:
        activation = {key: celpy.json_to_cel(value) for key, value in d.items()}
        try:
            if bool(program.evaluate(activation)):
                out.append(d)
        except celpy.CELEvalError:
            continue  # expression referenced an absent field -> not a match
    return out


def _apply_order(items: list[dict[str, Any]], order_by: str | None) -> list[dict[str, Any]]:
    if not order_by:
        return items
    field, _, direction = order_by.strip().partition(" ")
    reverse = direction.strip().upper() == "DESC"
    return sorted(items, key=lambda d: (extract_path(d, field) or [""])[0], reverse=reverse)


__all__ = ["InMemorySearchProvider", "EntriesSource"]
