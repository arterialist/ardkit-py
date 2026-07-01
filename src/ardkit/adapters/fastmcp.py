"""Adapter for the standalone ``fastmcp`` package.

The standalone ``fastmcp.FastMCP`` and the official SDK's ``mcp.server.fastmcp``
expose compatible-enough surfaces that :func:`~ardkit.adapters.mcp_sdk.from_mcp_server`
handles both. :func:`from_fastmcp` is a clearly-named alias so callers can be
explicit about which framework they're wiring.
"""

from __future__ import annotations

from typing import Any

from ..models import CatalogEntry
from .mcp_sdk import from_mcp_server


def from_fastmcp(server: Any, **kwargs: Any) -> CatalogEntry:
    """Build an MCP server-card entry from a ``fastmcp.FastMCP`` instance.

    See :func:`~ardkit.adapters.mcp_sdk.from_mcp_server` for accepted keywords.
    """
    return from_mcp_server(server, **kwargs)


__all__ = ["from_fastmcp"]
