"""ardkit — ARD (Agentic Resource Discovery) publisher & registry toolkit.

Make any FastAPI / FastMCP / AG2 backend an ARD *publisher* in a few lines:

>>> from ardkit import Catalog
>>> from ardkit.integrations.fastapi import mount_ard
>>> cat = Catalog(host="Acme AI", publisher="acme.com")
>>> _ = cat.add_mcp_server(
...     name="Billing", url="https://acme.com/mcp",
...     capabilities=["create_invoice"],
...     representative_queries=["create an invoice", "show unpaid invoices"],
... )
>>> # mount_ard(app, cat)  # serves /.well-known/ai-catalog.json + robots.txt

See https://agenticresourcediscovery.org/spec/ for the protocol.
"""

from __future__ import annotations

from . import media_types
from .__about__ import __version__
from .catalog import Catalog, make_urn, slugify
from .discovery import (
    agentmap_line,
    augment_robots,
    dns_records,
    link_tag,
    well_known_url,
)
from .errors import (
    ArdError,
    InvalidArgument,
    NotFound,
    NotImplementedByServer,
    RateLimitExceeded,
    Unauthenticated,
    ValidationError,
)
from .models import (
    SPEC_VERSION,
    Attestation,
    CatalogEntry,
    CatalogManifest,
    HostInfo,
    ProvenanceLink,
    TrustManifest,
    TrustSchema,
)

__all__ = [
    "__version__",
    "SPEC_VERSION",
    "Catalog",
    "make_urn",
    "slugify",
    "CatalogManifest",
    "CatalogEntry",
    "HostInfo",
    "TrustManifest",
    "TrustSchema",
    "Attestation",
    "ProvenanceLink",
    "media_types",
    "agentmap_line",
    "augment_robots",
    "dns_records",
    "link_tag",
    "well_known_url",
    "ArdError",
    "InvalidArgument",
    "Unauthenticated",
    "NotFound",
    "RateLimitExceeded",
    "NotImplementedByServer",
    "ValidationError",
]
