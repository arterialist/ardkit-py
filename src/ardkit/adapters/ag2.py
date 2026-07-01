"""Adapter for AG2 / AutoGen agents → A2A agent-card entries.

Duck-types the agent object (``.name``, ``.description``/``.system_message``) so
it works across AG2 versions without importing ``ag2``. Each agent becomes one
``application/a2a-agent-card+json`` entry.
"""

from __future__ import annotations

from typing import Any

from .. import media_types
from ..catalog import make_urn
from ..models import CatalogEntry


def _agent_name(agent: Any, fallback: str) -> str:
    return str(getattr(agent, "name", None) or fallback)


def _agent_description(agent: Any) -> str | None:
    for attr in ("description", "system_message", "system_prompt"):
        value = getattr(agent, attr, None)
        if value:
            return str(value)
    return None


def from_ag2_agent(
    agent: Any,
    *,
    url: str | None = None,
    data: dict[str, Any] | None = None,
    publisher: str | None = None,
    identifier: str | None = None,
    name: str | None = None,
    namespace: str = "agent",
    description: str | None = None,
    capabilities: list[str] | None = None,
    tags: list[str] | None = None,
    representative_queries: list[str] | None = None,
    version: str | None = None,
    **extra: Any,
) -> CatalogEntry:
    """Build an A2A agent-card entry from a single AG2/AutoGen agent."""
    display_name = name or _agent_name(agent, "Agent")
    if identifier is None:
        if not publisher:
            raise ValueError("from_ag2_agent needs publisher=... or identifier=... to mint a URN")
        identifier = make_urn(publisher, namespace, display_name)

    fields: dict[str, Any] = {
        "identifier": identifier,
        "display_name": display_name,
        "type": media_types.A2A_AGENT_CARD,
        "description": description if description is not None else _agent_description(agent),
        "capabilities": capabilities,
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


def from_ag2_agents(
    agents: list[Any],
    *,
    publisher: str | None = None,
    url_for: Any = None,
    **common: Any,
) -> list[CatalogEntry]:
    """Map a list of AG2 agents to entries.

    ``url_for`` is an optional ``callable(agent) -> url`` to assign each agent's
    endpoint; without it, entries are inlined via ``data`` only if provided per
    call, so pass ``url_for`` or per-agent handling for real deployments.
    """
    entries: list[CatalogEntry] = []
    for agent in agents:
        kwargs = dict(common)
        if url_for is not None:
            kwargs["url"] = url_for(agent)
        entries.append(from_ag2_agent(agent, publisher=publisher, **kwargs))
    return entries


__all__ = ["from_ag2_agent", "from_ag2_agents"]
