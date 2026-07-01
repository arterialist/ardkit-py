"""IANA media-type constants used to type ARD catalog entries.

ARD identifies every artifact by its media ``type`` rather than constraining the
inner schema (the "artifact-agnostic envelope" principle). The values below are
the de-facto community types referenced by the spec; ``type`` is a free string,
so custom ``application/<vendor>+json`` types are equally valid.
"""

from __future__ import annotations

#: An A2A (Agent-to-Agent) Agent Card.
A2A_AGENT_CARD = "application/a2a-agent-card+json"
#: An MCP (Model Context Protocol) server card.
MCP_SERVER_CARD = "application/mcp-server-card+json"
#: A nested ai-catalog (a bundle of further entries).
AI_CATALOG = "application/ai-catalog+json"
#: An ARD search registry endpoint.
AI_REGISTRY = "application/ai-registry+json"
#: A reusable skill / plugin.
AI_SKILL = "application/ai-skill"

#: Registry referral ``type`` values accepted by the spec.
REGISTRY_TYPES = frozenset({"application/ai-registry", "application/ai-registry+json"})

__all__ = [
    "A2A_AGENT_CARD",
    "MCP_SERVER_CARD",
    "AI_CATALOG",
    "AI_REGISTRY",
    "AI_SKILL",
    "REGISTRY_TYPES",
]
