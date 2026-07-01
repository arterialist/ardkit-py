"""Adapters that turn framework objects into ARD catalog entries.

* :func:`from_mcp_server` / :func:`from_fastmcp` — MCP servers (official ``mcp``
  SDK ``FastMCP`` or the standalone ``fastmcp`` package) → an
  ``application/mcp-server-card+json`` entry whose ``capabilities`` are the tool
  names.
* :func:`from_ag2_agent` / :func:`from_ag2_agents` — AG2 / AutoGen agents →
  ``application/a2a-agent-card+json`` entries.
"""

from .ag2 import from_ag2_agent, from_ag2_agents
from .fastmcp import from_fastmcp
from .mcp_sdk import from_mcp_server, mcp_tool_names

__all__ = [
    "from_mcp_server",
    "from_fastmcp",
    "mcp_tool_names",
    "from_ag2_agent",
    "from_ag2_agents",
]
