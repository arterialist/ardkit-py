"""One-call FastAPI wiring: ``mount_ard(app, catalog)``.

Registers, on an existing FastAPI app:

* ``GET /.well-known/ai-catalog.json`` — the manifest, with
  ``Content-Type: application/json`` and ``Access-Control-Allow-Origin: *`` so
  crawlers can fetch it cross-origin (per the publishing guide).
* ``GET /robots.txt`` — optionally, an ``Agentmap:`` directive (merged with any
  base robots content you supply).
* The registry endpoints (``/search`` etc.) — optionally, when you pass a
  ``RegistryService`` or ``SearchProvider``.

The ``catalog`` source may be a :class:`~ardkit.catalog.Catalog`, a
:class:`~ardkit.models.CatalogManifest`, a plain dict, or a zero-arg callable
returning any of those (for dynamic, DB-backed catalogs).
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, Response

from ..adapters import from_ag2_agent, from_mcp_server
from ..catalog import Catalog
from ..discovery import WELL_KNOWN_PATH, augment_robots, well_known_url
from ..models import CatalogManifest
from ..registry.fastapi import build_registry_router
from ..registry.service import RegistryService

logger = logging.getLogger("ardkit")

#: Default catalog ``Cache-Control``: short fresh window + long stale-while-revalidate.
DEFAULT_CATALOG_CACHE = "public, max-age=300, stale-while-revalidate=86400"

CatalogSource = (
    Catalog
    | CatalogManifest
    | dict
    | Callable[[], Catalog | CatalogManifest | dict | Awaitable[Any]]
)


def _manifest_etag(body: bytes) -> str:
    """Strong-ish weak ETag from a SHA-256 of the serialized manifest."""
    digest = hashlib.sha256(body).hexdigest()[:32]
    return f'W/"{digest}"'


def _resolve_to_dict(source: Any) -> Any:
    if isinstance(source, Catalog):
        return source.to_dict()
    if isinstance(source, CatalogManifest):
        return source.to_dict()
    if isinstance(source, dict):
        return source
    raise TypeError(f"unsupported catalog source: {type(source)!r}")


async def _materialise(source: CatalogSource) -> dict[str, Any]:
    value: Any = source() if callable(source) else source
    if hasattr(value, "__await__"):
        value = await value
    return _resolve_to_dict(value)


def add_catalog_route(
    app: FastAPI,
    catalog: CatalogSource,
    *,
    path: str = WELL_KNOWN_PATH,
    cors_origin: str = "*",
    cache_control: str | None = DEFAULT_CATALOG_CACHE,
) -> None:
    """Serve the manifest as a cacheable JSON document at ``path``.

    Emits ``Content-Type: application/json``, CORS, a weak ``ETag`` and
    ``Cache-Control``, and answers conditional ``If-None-Match`` with ``304``.
    Use this directly (e.g. ``path="/api/ard/ai-catalog.json"``) to expose the
    catalog *origin* on a backend host when discovery is published elsewhere.
    """

    @app.get(path, include_in_schema=False)
    async def _ai_catalog(request: Request) -> Response:  # pragma: no cover - TestClient
        manifest = await _materialise(catalog)
        body = json.dumps(manifest, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        etag = _manifest_etag(body)
        headers = {"Access-Control-Allow-Origin": cors_origin, "ETag": etag}
        if cache_control:
            headers["Cache-Control"] = cache_control
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(content=body, media_type="application/json", headers=headers)


def mount_ard(
    app: FastAPI,
    catalog: CatalogSource,
    *,
    well_known_path: str = WELL_KNOWN_PATH,
    serve_robots: bool = True,
    robots_base: str | None = None,
    registry: RegistryService | Any | None = None,
    registry_prefix: str = "/ard",
    registry_source_url: str | None = None,
    enable_explore: bool = True,
    enable_agents: bool = True,
    cors_origin: str = "*",
    cache_control: str | None = DEFAULT_CATALOG_CACHE,
) -> None:
    """Wire ARD publishing (and optionally a registry) onto a FastAPI ``app``.

    Args:
        app: The FastAPI application to mount onto.
        catalog: Catalog/manifest/dict or (async) callable returning one.
        registry: A :class:`RegistryService`, or a bare ``SearchProvider`` (then
            ``registry_source_url`` is required to stamp result ``source``).
        registry_prefix: Path prefix for the registry endpoints.
        cache_control: ``Cache-Control`` for the manifest (set ``None`` to omit).
    """
    add_catalog_route(
        app,
        catalog,
        path=well_known_path,
        cors_origin=cors_origin,
        cache_control=cache_control,
    )

    if serve_robots:

        @app.get("/robots.txt", include_in_schema=False)
        async def _robots(request: Request) -> PlainTextResponse:  # pragma: no cover
            origin = str(request.base_url).rstrip("/")
            content = augment_robots(robots_base, well_known_url(origin))
            return PlainTextResponse(content)

    if registry is not None:
        service = registry
        if not isinstance(service, RegistryService):
            if not registry_source_url:
                raise ValueError(
                    "registry_source_url is required when passing a bare SearchProvider"
                )
            service = RegistryService(service, source=registry_source_url)
        router = build_registry_router(
            service, enable_explore=enable_explore, enable_agents=enable_agents
        )
        app.include_router(router, prefix=registry_prefix)


def _join_path(mount_path: str, inner: str | None) -> str:
    if not inner or inner == "/":
        return mount_path
    return mount_path.rstrip("/") + "/" + inner.lstrip("/")


def _reverse_map_fastmcp(asgi: Any, depth: int = 8) -> tuple[Any, str | None] | None:
    """Walk an ASGI/middleware chain to a FastMCP and return ``(server, path)``.

    Relies on fastmcp's ``http_app()`` storing ``app.state.fastmcp_server`` (the
    instance) and ``app.state.path`` (its streamable sub-path). Returns ``None``
    if the chain isn't a FastMCP app.
    """
    cur = asgi
    for _ in range(depth):
        state = getattr(cur, "state", None)
        server = getattr(state, "fastmcp_server", None) if state is not None else None
        if server is not None:
            return server, getattr(state, "path", None)
        nxt = getattr(cur, "app", None)
        if nxt is None or nxt is cur:
            break
        cur = nxt
    return None


def mounted_mcps(app: FastAPI) -> list[tuple[Any, str]]:
    """Every FastMCP mounted on ``app`` as ``(server, endpoint_path)`` pairs.

    Identity-based via fastmcp's app state, so each server maps to the exact route
    it's mounted at, including the streamable sub-path (mount ``/mcp/x`` + ``/mcp``
    → ``/mcp/x/mcp``). Middleware wrappers (e.g. auth) are unwrapped.

    Read fresh each call, so it reflects servers mounted/unmounted at runtime —
    use it to build a *dynamic* catalog source for hosts whose MCPs come and go.
    """
    out: list[tuple[Any, str]] = []
    seen: set[int] = set()
    for route in getattr(app, "routes", []):
        if route.__class__.__name__ != "Mount":
            continue
        mount_path = getattr(route, "path", None)
        sub = getattr(route, "app", None)
        if not mount_path or sub is None:
            continue
        found = _reverse_map_fastmcp(sub)
        if found is None or id(found[0]) in seen:
            continue
        server, inner = found
        seen.add(id(server))
        out.append((server, _join_path(mount_path, inner)))
    return out


def _ag2_inline_card(agent: Any) -> dict[str, Any]:
    """Minimal inline A2A card for an agent that has no HTTP endpoint."""
    card: dict[str, Any] = {"name": str(getattr(agent, "name", None) or "Agent")}
    desc = getattr(agent, "description", None) or getattr(agent, "system_message", None)
    if desc:
        card["description"] = str(desc)
    return card


def publish(
    app: FastAPI,
    *,
    host: str,
    publisher: str,
    base_url: str | None = None,
    identifier: str | None = None,
    mcps: Sequence[Any] | None = None,
    agents: Sequence[Any] | None = None,
    introspect: bool = True,
    document_path: str | None = None,
    registry: Any | None = None,
    **mount_kwargs: Any,
) -> Catalog:
    """Enrich a FastAPI app with ARD discovery in a single call.

    ``publish`` never mounts anything — the MCP servers that should be exposed are
    already mounted on ``app`` by you. It reads the route table, maps each mounted
    FastMCP back to its instance (identity-based, via fastmcp app state), and
    publishes it with the correct public URL. Two ways to choose what's exposed:

    - **Introspection** (``introspect=True``, the default) — expose *every*
      FastMCP mounted on ``app``, with ``capabilities`` = tool names.
    - **Explicit list** (``mcps=[server, ...]``) — pass FastMCP instances to
      expose; any instance that isn't actually mounted on ``app`` is ignored (with
      a warning). Set ``introspect=False`` to expose *only* these.

    ``agents`` accepts framework agent instances (AG2 / duck-typed) published as
    A2A cards with an inline card (they have no HTTP mount).

    URLs are built from each server's mount path joined to ``base_url`` — the
    public origin where the app is reachable (e.g. ``"https://app.acme.com"``),
    which differs from the bind address behind a proxy. Provide it.

    Then the catalog is served on ``app``: the well-known route + robots, or — when
    ``document_path`` is set — a cacheable document at that path (content-origin
    mode, no robots), plus any ``registry`` endpoints.

    Returns the live :class:`~ardkit.catalog.Catalog`; later ``.add_*`` calls show
    up on the next request.

    Example:
        >>> publish(app, host="Acme AI", publisher="acme.com",
        ...         base_url="https://app.acme.com")  # exposes mounted MCPs
    """
    catalog = Catalog(
        host=host,
        publisher=publisher,
        identifier=identifier or f"did:web:{publisher}",
    )

    def _absolutize(path: str) -> str | None:
        if "://" in path:
            return path
        if base_url:
            return base_url.rstrip("/") + "/" + path.lstrip("/")
        return None

    mounted = mounted_mcps(app)
    by_id = {id(server): path for server, path in mounted}

    selected: list[tuple[Any, str]] = []
    chosen: set[int] = set()

    if mcps is not None:
        for instance in mcps:
            path = by_id.get(id(instance))
            if path is None:
                logger.warning(
                    "ardkit.publish: MCP %r is not mounted on the app; ignoring it.",
                    getattr(instance, "name", instance),
                )
                continue
            if id(instance) not in chosen:
                chosen.add(id(instance))
                selected.append((instance, path))

    if introspect:
        for server, path in mounted:
            if id(server) not in chosen:
                chosen.add(id(server))
                selected.append((server, path))

    for server, path in selected:
        url = _absolutize(path)
        if url is None:
            logger.warning(
                "ardkit.publish: cannot build a URL for a mounted MCP at %s "
                "(pass base_url=...); skipping it.",
                path,
            )
            continue
        catalog.add(from_mcp_server(server, url=url, publisher=publisher))

    for agent in agents or []:
        catalog.add(from_ag2_agent(agent, publisher=publisher, data=_ag2_inline_card(agent)))

    if document_path:
        add_catalog_route(app, catalog, path=document_path)
    else:
        mount_ard(app, catalog, registry=registry, **mount_kwargs)
    return catalog


__all__ = [
    "mount_ard",
    "add_catalog_route",
    "publish",
    "mounted_mcps",
    "CatalogSource",
    "DEFAULT_CATALOG_CACHE",
]
