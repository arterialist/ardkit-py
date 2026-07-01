"""Adapter for MCP servers (official ``mcp`` SDK ``FastMCP``).

Introspects a server's registered tools (best-effort across SDK versions) and
builds a single ``application/mcp-server-card+json`` catalog entry whose
``capabilities`` list is the tool names. No hard dependency on ``mcp``: the
server object is duck-typed, so it also works with any custom-built MCP server
object that exposes a tool manager.
"""

from __future__ import annotations

import inspect
from typing import Any

from .. import media_types
from ..catalog import make_urn
from ..models import CatalogEntry


def mcp_tool_names(server: Any) -> list[str]:
    """Best-effort, synchronous extraction of tool names from an MCP server.

    Handles both FastMCP (v2) — whose ``ToolManager`` holds a sync ``_tools``
    dict and only an *async* ``get_tools()`` — and the official ``mcp`` SDK,
    whose ``ToolManager`` exposes a sync ``list_tools()``. Never awaits: a
    coroutine result is ignored so this stays callable from sync request paths.
    """
    for attr in ("_tool_manager", "tool_manager"):
        manager = getattr(server, attr, None)
        if manager is None:
            continue
        names = _names_from_holder(manager)
        if names:
            return names
    # Server-level fallbacks (custom/duck-typed servers).
    return _names_from_holder(server)


def _names_from_holder(holder: Any) -> list[str]:
    # FastMCP v2: a sync ``_tools`` dict keyed by tool key, values are Tools.
    tools = getattr(holder, "_tools", None)
    if tools is None:
        tools = getattr(holder, "tools", None)
        if callable(tools):  # avoid bound methods named ``tools``
            tools = None
    if isinstance(tools, dict) and tools:
        return [n for n in (_tool_name(t) for t in tools.values()) if n]
    if isinstance(tools, (list, tuple)) and tools:
        return [n for n in (_tool_name(t) for t in tools) if n]
    # Official mcp SDK / older FastMCP: a sync ``list_tools()``.
    lister = getattr(holder, "list_tools", None)
    if callable(lister):
        try:
            result: Any = lister()
            if not inspect.isawaitable(result):
                return [n for n in (_tool_name(t) for t in result) if n]
        except Exception:  # noqa: BLE001 - introspection is best-effort
            pass
    return []


def _tool_name(tool: Any) -> str:
    if isinstance(tool, str):
        return tool
    return str(
        getattr(tool, "name", "") or (tool.get("name", "") if isinstance(tool, dict) else "")
    )


def _server_name(server: Any, fallback: str) -> str:
    return str(getattr(server, "name", None) or fallback)


def from_mcp_server(
    server: Any,
    *,
    url: str | None = None,
    data: dict[str, Any] | None = None,
    publisher: str | None = None,
    identifier: str | None = None,
    name: str | None = None,
    namespace: str = "mcp",
    description: str | None = None,
    capabilities: list[str] | None = None,
    tags: list[str] | None = None,
    representative_queries: list[str] | None = None,
    version: str | None = None,
    **extra: Any,
) -> CatalogEntry:
    """Build an MCP server-card entry from an MCP server object.

    Provide ``url`` (the server's HTTP endpoint) or ``data`` (an inline card).
    ``capabilities`` defaults to the server's introspected tool names.
    """
    display_name = name or _server_name(server, "MCP Server")
    caps = capabilities if capabilities is not None else mcp_tool_names(server)
    if identifier is None:
        if not publisher:
            raise ValueError("from_mcp_server needs publisher=... or identifier=... to mint a URN")
        identifier = make_urn(publisher, namespace, display_name)

    fields: dict[str, Any] = {
        "identifier": identifier,
        "display_name": display_name,
        "type": media_types.MCP_SERVER_CARD,
        "description": description,
        "capabilities": caps or None,
        "tags": tags,
        "representative_queries": representative_queries,
        "version": version,
        **extra,
    }
    if url is not None:
        fields["url"] = url
    if data is not None:
        fields["data"] = data
    return CatalogEntry.model_validate({k: v for k, v in fields.items() if v is not None})


__all__ = ["from_mcp_server", "mcp_tool_names"]
