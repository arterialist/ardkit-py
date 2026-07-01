"""Helpers for the ARD discovery hints that point crawlers at a catalog.

Beyond hosting the manifest at ``/.well-known/ai-catalog.json``, the spec defines
several optional advertisement mechanisms. These helpers render them:

* ``robots.txt`` ``Agentmap:`` directive (:func:`agentmap_line`, :func:`augment_robots`)
* HTML ``<link rel="ai-catalog">`` tag (:func:`link_tag`)
* DNS hint records (:func:`dns_records`)
"""

from __future__ import annotations

WELL_KNOWN_PATH = "/.well-known/ai-catalog.json"


def well_known_url(origin: str) -> str:
    """Return the canonical well-known catalog URL for an ``origin``."""
    return origin.rstrip("/") + WELL_KNOWN_PATH


def agentmap_line(catalog_url: str) -> str:
    """Render the ``robots.txt`` directive advertising a catalog."""
    return f"Agentmap: {catalog_url}"


def augment_robots(existing: str | None, catalog_url: str) -> str:
    """Add an ``Agentmap:`` directive to existing robots.txt content (idempotent)."""
    line = agentmap_line(catalog_url)
    body = (existing or "").rstrip()
    for existing_line in body.splitlines():
        if existing_line.strip().lower() == line.lower():
            return body + "\n"
    if body:
        return body + "\n" + line + "\n"
    return line + "\n"


def link_tag(catalog_url: str) -> str:
    """Render an HTML ``<link rel="ai-catalog">`` tag for a page ``<head>``."""
    return f'<link rel="ai-catalog" href="{catalog_url}">'


def dns_records(
    domain: str, *, catalog_url: str | None = None, search_url: str | None = None
) -> list[str]:
    """Render DNS TXT hint records for catalog and/or registry discovery.

    Returns ready-to-paste zone lines for ``_catalog._agents.<domain>`` (static
    manifest) and ``_search._agents.<domain>`` (dynamic registry).
    """
    records: list[str] = []
    if catalog_url:
        records.append(f'_catalog._agents.{domain}. IN TXT "url={catalog_url}"')
    if search_url:
        records.append(f'_search._agents.{domain}. IN TXT "url={search_url}"')
    return records


__all__ = [
    "WELL_KNOWN_PATH",
    "well_known_url",
    "agentmap_line",
    "augment_robots",
    "link_tag",
    "dns_records",
]
