"""Pydantic models mirroring the ARD ``ai-catalog.json`` manifest schema.

These models are the single in-memory representation used by the builder
(:mod:`ardkit.catalog`), the framework adapters, and the registry layer. They
mirror ``spec/schemas/ai-catalog.schema.json`` (vendored under
``ardkit/schemas``) field-for-field. Pythonic ``snake_case`` attribute names are
aliased to the spec's ``camelCase`` JSON keys; dump with ``by_alias=True``
(see :meth:`CatalogManifest.to_dict`).

The models are intentionally lenient on read (unknown keys are preserved on
entries) — strict spec conformance is enforced separately by
:mod:`ardkit.validation`, which runs the vendored JSON Schema.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from .__about__ import __version__

SPEC_VERSION = "1.0"

# Matches the ``identifier`` pattern in ai-catalog.schema.json:
#   urn:air:<publisher>(:<segment>)+
URN_PATTERN = re.compile(r"^urn:air:[a-zA-Z0-9.-]+(:[a-zA-Z0-9._-]+)+$")

MetadataValue = str | int | float | bool | None


class _ArdModel(BaseModel):
    """Base model: camelCase JSON aliases, accept snake_case or camelCase input."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class TrustSchema(_ArdModel):
    identifier: str
    version: str
    governance_uri: str | None = None
    verification_methods: list[str] | None = None


class Attestation(_ArdModel):
    type: str
    uri: str
    media_type: str
    digest: str | None = None


class ProvenanceLink(_ArdModel):
    relation: Literal["derivedFrom", "publishedFrom", "copiedFrom"]
    source_id: str
    source_digest: str | None = None


class TrustManifest(_ArdModel):
    identity: str
    identity_type: Literal["spiffe", "did", "https", "other"] | None = None
    trust_schema: TrustSchema | None = None
    attestations: list[Attestation] | None = None
    provenance: list[ProvenanceLink] | None = None
    signature: str | None = None


class HostInfo(_ArdModel):
    display_name: str
    identifier: str | None = None
    documentation_url: str | None = None
    logo_url: str | None = None
    trust_manifest: TrustManifest | None = None


class CatalogEntry(_ArdModel):
    # Entries may carry response-only fields (score/source) and custom keys, so
    # extra attributes are preserved rather than dropped.
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )

    identifier: str
    display_name: str
    type: str
    url: str | None = None
    data: dict[str, Any] | None = None
    description: str | None = None
    tags: list[str] | None = None
    capabilities: list[str] | None = None
    representative_queries: Annotated[list[str], Field(min_length=2, max_length=5)] | None = None
    version: str | None = None
    updated_at: datetime | None = None
    metadata: dict[str, MetadataValue] | None = None
    trust_manifest: TrustManifest | None = None

    @field_validator("identifier")
    @classmethod
    def _validate_urn(cls, v: str) -> str:
        if not URN_PATTERN.match(v):
            raise ValueError(
                f"identifier {v!r} is not a valid ARD URN "
                "(expected urn:air:<publisher>:<namespace>:<name>)"
            )
        return v

    @model_validator(mode="after")
    def _exactly_one_locator(self) -> CatalogEntry:
        has_url = self.url is not None
        has_data = self.data is not None
        if has_url == has_data:
            raise ValueError("catalog entry must set exactly one of 'url' or 'data'")
        return self


class CatalogManifest(_ArdModel):
    spec_version: Literal["1.0"] = SPEC_VERSION
    host: HostInfo | None = None
    entries: list[CatalogEntry] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a spec-shaped dict (camelCase keys, no ``None`` fields)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CatalogManifest:
        return cls.model_validate(data)


__all__ = [
    "SPEC_VERSION",
    "URN_PATTERN",
    "MetadataValue",
    "TrustSchema",
    "Attestation",
    "ProvenanceLink",
    "TrustManifest",
    "HostInfo",
    "CatalogEntry",
    "CatalogManifest",
    "__version__",
]
