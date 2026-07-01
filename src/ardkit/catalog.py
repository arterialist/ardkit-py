"""Fluent builder for an ARD ``ai-catalog.json`` manifest.

``Catalog`` accumulates :class:`~ardkit.models.CatalogEntry` objects and renders
a :class:`~ardkit.models.CatalogManifest`. Convenience methods
(:meth:`add_mcp_server`, :meth:`add_a2a_agent`, :meth:`add_skill`,
:meth:`add_registry`) set sensible ``type`` defaults and auto-mint URN
identifiers from the host's publisher domain so the common case is a one-liner.

Example
-------
>>> cat = Catalog(host="Acme AI", publisher="acme.com")
>>> _ = cat.add_mcp_server(
...     name="Billing",
...     url="https://acme.com/mcp",
...     capabilities=["create_invoice", "list_invoices"],
...     representative_queries=["create an invoice", "show unpaid invoices"],
... )
>>> cat.to_manifest().spec_version
'1.0'
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from . import media_types
from .models import CatalogEntry, CatalogManifest, HostInfo

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")


def slugify(value: str) -> str:
    """Lower-case ``value`` and reduce it to URN-safe characters."""
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "resource"


def make_urn(publisher: str, *segments: str) -> str:
    """Build an ARD URN ``urn:air:<publisher>:<segment>...``.

    ``publisher`` is normally the publisher's FQDN. At least one trailing
    segment is required by the spec; segments are slugified.
    """
    if not publisher:
        raise ValueError("publisher (e.g. a domain) is required to build a URN")
    parts = [slugify(s) for s in segments if s]
    if not parts:
        raise ValueError("at least one namespace/name segment is required")
    return ":".join(["urn:air", publisher, *parts])


class Catalog:
    """Mutable builder that produces a :class:`CatalogManifest`."""

    def __init__(
        self,
        host: HostInfo | str | None = None,
        *,
        publisher: str | None = None,
        identifier: str | None = None,
        documentation_url: str | None = None,
        logo_url: str | None = None,
    ):
        if isinstance(host, HostInfo):
            self.host: HostInfo | None = host
        elif isinstance(host, str):
            self.host = HostInfo(
                display_name=host,
                identifier=identifier,
                documentation_url=documentation_url,
                logo_url=logo_url,
            )
        else:
            self.host = None
        # The publisher (FQDN) used to mint URNs when an explicit identifier is
        # not supplied. Falls back to the host identifier's domain.
        self.publisher = publisher or _publisher_from_identifier(identifier)
        self._entries: list[CatalogEntry] = []

    # -- low level -------------------------------------------------------
    def add(self, entry: CatalogEntry) -> CatalogEntry:
        """Append an already-built :class:`CatalogEntry`."""
        self._entries.append(entry)
        return entry

    def add_entry(self, **kwargs: Any) -> CatalogEntry:
        """Build and append a :class:`CatalogEntry` from keyword fields.

        ``identifier`` may be omitted if ``publisher``/``namespace``/``name`` are
        provided (or set on the catalog), in which case a URN is minted.
        """
        kwargs = self._ensure_identifier(kwargs)
        return self.add(CatalogEntry.model_validate(kwargs))

    # -- typed helpers ---------------------------------------------------
    def add_mcp_server(self, **kwargs: Any) -> CatalogEntry:
        """Add an ``application/mcp-server-card+json`` entry."""
        kwargs.setdefault("type", media_types.MCP_SERVER_CARD)
        kwargs.setdefault("namespace", "mcp")
        return self.add_entry(**kwargs)

    def add_a2a_agent(self, **kwargs: Any) -> CatalogEntry:
        """Add an ``application/a2a-agent-card+json`` entry."""
        kwargs.setdefault("type", media_types.A2A_AGENT_CARD)
        kwargs.setdefault("namespace", "agent")
        return self.add_entry(**kwargs)

    def add_skill(self, **kwargs: Any) -> CatalogEntry:
        """Add an ``application/ai-skill`` entry."""
        kwargs.setdefault("type", media_types.AI_SKILL)
        kwargs.setdefault("namespace", "skill")
        return self.add_entry(**kwargs)

    def add_registry(self, **kwargs: Any) -> CatalogEntry:
        """Advertise an ARD search registry (``application/ai-registry+json``)."""
        kwargs.setdefault("type", media_types.AI_REGISTRY)
        kwargs.setdefault("namespace", "registry")
        return self.add_entry(**kwargs)

    # -- output ----------------------------------------------------------
    def to_manifest(self, *, touch: bool = False) -> CatalogManifest:
        """Render a :class:`CatalogManifest`.

        If ``touch`` is set, entries without ``updated_at`` get the current UTC
        timestamp.
        """
        entries = self._entries
        if touch:
            now = datetime.now().astimezone()
            entries = [e.model_copy(update={"updated_at": e.updated_at or now}) for e in entries]
        return CatalogManifest(host=self.host, entries=list(entries))

    def to_dict(self, *, touch: bool = False) -> dict[str, Any]:
        return self.to_manifest(touch=touch).to_dict()

    def to_json(self, *, indent: int | None = 2, touch: bool = False) -> str:
        return self.to_manifest(touch=touch).to_json(indent=indent)

    @property
    def entries(self) -> list[CatalogEntry]:
        return list(self._entries)

    # -- internals -------------------------------------------------------
    def _ensure_identifier(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs = dict(kwargs)
        namespace = kwargs.pop("namespace", None)
        name = kwargs.get("name")
        # Allow `name=` as a friendly alias for displayName when not given.
        if name is not None and not (kwargs.get("display_name") or kwargs.get("displayName")):
            kwargs["display_name"] = name
        kwargs.pop("name", None)

        if not (kwargs.get("identifier")):
            publisher = kwargs.pop("publisher", None) or self.publisher
            if not publisher:
                raise ValueError(
                    "cannot mint a URN: pass identifier=..., or set a publisher on "
                    "the Catalog / entry (e.g. publisher='acme.com')"
                )
            label = name or kwargs.get("display_name") or kwargs.get("displayName")
            if not label:
                raise ValueError("entry needs a name/display_name to mint an identifier")
            segments = [s for s in (namespace, str(label)) if s]
            kwargs["identifier"] = make_urn(publisher, *segments)
        else:
            kwargs.pop("publisher", None)
        return kwargs


def _publisher_from_identifier(identifier: str | None) -> str | None:
    """Best-effort extraction of an FQDN from a host identifier like did:web."""
    if not identifier:
        return None
    if identifier.startswith("did:web:"):
        return identifier.removeprefix("did:web:").split(":")[0].replace("%3A", ":")
    if "://" in identifier:
        return identifier.split("://", 1)[1].split("/")[0]
    return identifier


__all__ = ["Catalog", "make_urn", "slugify"]
