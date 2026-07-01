"""FastAPI router exposing the ARD registry endpoints over a RegistryService.

``build_registry_router(service)`` returns an ``APIRouter`` with ``POST /search``
(required), and optionally ``POST /explore`` and ``GET /agents``. ARD errors are
rendered as ``{errorCode, message}`` with the spec HTTP status.
"""

from __future__ import annotations

from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ..errors import ArdError, InvalidArgument
from .service import RegistryService


def build_registry_router(
    service: RegistryService,
    *,
    enable_explore: bool = True,
    enable_agents: bool = True,
    tags: list[str] | None = None,
) -> APIRouter:
    """Build an APIRouter wired to ``service``. Requires the ``fastapi`` extra."""
    router_tags: list[Any] = list(tags) if tags else ["ard"]
    router = APIRouter(tags=router_tags)

    def _error(exc: ArdError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_wire())

    @router.post("/search")
    async def search(request: Request) -> Any:
        try:
            payload = await _json_body(request)
            return await service.search(payload)
        except ArdError as exc:
            return _error(exc)

    if enable_explore:

        @router.post("/explore")
        async def explore(request: Request) -> Any:
            try:
                payload = await _json_body(request)
                return await service.explore(payload)
            except ArdError as exc:
                return _error(exc)

    if enable_agents:

        @router.get("/agents")
        async def agents(
            filter: str | None = Query(default=None),
            orderBy: str | None = Query(default=None),  # noqa: N803 - ARD wire name
            pageSize: int = Query(default=20, ge=1, le=100),  # noqa: N803
            pageToken: str | None = Query(default=None),  # noqa: N803
        ) -> Any:
            try:
                return await service.list_agents(
                    filter=filter,
                    order_by=orderBy,
                    page_size=pageSize,
                    page_token=pageToken,
                )
            except ArdError as exc:
                return _error(exc)

    return router


async def _json_body(request: Any) -> dict[str, Any]:
    try:
        body = await request.json()
    except (JSONDecodeError, ValueError) as exc:
        raise InvalidArgument("request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise InvalidArgument("request body must be a JSON object")
    return body


__all__ = ["build_registry_router"]
