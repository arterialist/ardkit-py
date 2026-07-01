"""Framework-agnostic ARD registry service.

:class:`RegistryService` turns raw request payloads into spec-compliant response
dicts by delegating ranking to a :class:`SearchProvider`. It owns request
validation, ``source`` stamping, federation/referral behaviour, and the optional
endpoints' 501 handling. The FastAPI router (:mod:`ardkit.registry.fastapi`) is a
thin adapter over this class.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ..errors import InvalidArgument, NotImplementedByServer
from .models import (
    ExploreRequest,
    SearchQuery,
    SearchRequest,
)
from .provider import SearchProvider, as_dict


class RegistryService:
    """Adapts a :class:`SearchProvider` to the ARD REST contract."""

    def __init__(
        self,
        provider: SearchProvider,
        *,
        source: str,
        referrals: list[dict[str, Any]] | None = None,
        max_page_size: int = 100,
    ):
        #: Endpoint URL stamped onto every result's ``source`` field.
        self.source = source
        self.provider = provider
        self.referrals = referrals or []
        self.max_page_size = max_page_size

    async def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = self._parse(SearchRequest, payload)
        page_size = min(request.page_size, self.max_page_size)
        query = SearchQuery(text=request.query.text, filter=_normalise_filter(request.query.filter))

        page = await self.provider.search(query, page_size=page_size, page_token=request.page_token)

        results: list[dict[str, Any]] = []
        for scored in page.items:
            item = dict(as_dict(scored.entry))
            item["score"] = int(scored.score)
            item["source"] = self.source
            results.append(item)

        response: dict[str, Any] = {"results": results}
        # Referrals are advertised in 'referrals' mode (and offered in 'auto').
        if request.federation in ("referrals", "auto") and self.referrals:
            response["referrals"] = self.referrals
        if page.next_page_token:
            response["pageToken"] = page.next_page_token
        return response

    async def explore(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = self._parse(ExploreRequest, payload)
        explore = getattr(self.provider, "explore", None)
        if explore is None:
            raise NotImplementedByServer("explore is not implemented by this registry")
        text = request.query.text if request.query else ""
        query = SearchQuery(
            text=text or "",
            filter=_normalise_filter(request.query.filter) if request.query else {},
        )
        fields = [(f.field, f.limit, f.min_count) for f in request.result_type.facets]
        try:
            facets = await explore(query, fields)
        except NotImplementedError as exc:
            raise NotImplementedByServer("explore is not implemented by this registry") from exc

        return {
            "resultType": "facets",
            "facets": {
                name: {
                    "buckets": [{"value": b.value, "count": b.count} for b in result.buckets],
                    "otherCount": result.other_count,
                }
                for name, result in facets.items()
            },
        }

    async def list_agents(
        self,
        *,
        filter: str | None = None,
        order_by: str | None = None,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        list_agents = getattr(self.provider, "list_agents", None)
        if list_agents is None:
            raise NotImplementedByServer("listing is not implemented by this registry")
        page_size = min(max(page_size, 1), self.max_page_size)
        try:
            result = await list_agents(
                filter=filter,
                order_by=order_by,
                page_size=page_size,
                page_token=page_token,
            )
        except NotImplementedError as exc:
            raise NotImplementedByServer("listing is not implemented by this registry") from exc

        response: dict[str, Any] = {"items": [as_dict(i) for i in result.items]}
        if result.total is not None:
            response["total"] = result.total
        if result.next_page_token:
            response["pageToken"] = result.next_page_token
        return response

    @staticmethod
    def _parse(model: type, payload: dict[str, Any]):
        try:
            return model.model_validate(payload)
        except PydanticValidationError as exc:
            raise InvalidArgument(_summarise(exc)) from exc


def _normalise_filter(raw: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        out[key] = [str(v) for v in value] if isinstance(value, list) else [str(value)]
    return out


def _summarise(exc: PydanticValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "<body>"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts) or "invalid request"


__all__ = ["RegistryService"]
