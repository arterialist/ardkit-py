"""Conformance validation against the vendored ARD JSON Schema.

:func:`validate_manifest` checks a manifest dict (or :class:`CatalogManifest`)
against ``schemas/ai-catalog.schema.json`` — the authoritative runtime contract
from the spec — and returns a list of human-readable errors (empty == valid).

Requires the ``jsonschema`` extra (``pip install "ardkit-ai[validation]"``).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

import jsonschema

from .errors import ValidationError
from .models import CatalogManifest


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Load the vendored ai-catalog JSON Schema."""
    text = resources.files("ardkit.schemas").joinpath("ai-catalog.schema.json").read_text("utf-8")
    return json.loads(text)


@lru_cache(maxsize=1)
def spec_version() -> str:
    return resources.files("ardkit.schemas").joinpath("SPEC_VERSION").read_text("utf-8").strip()


def _coerce(manifest: CatalogManifest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(manifest, CatalogManifest):
        return manifest.to_dict()
    return manifest


def validate_manifest(manifest: CatalogManifest | dict[str, Any]) -> list[str]:
    """Validate a manifest, returning a list of error messages (empty if valid)."""
    data = _coerce(manifest)
    validator = jsonschema.Draft202012Validator(load_schema())
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    return [_format_error(e) for e in errors]


def assert_valid(manifest: CatalogManifest | dict[str, Any]) -> None:
    """Raise :class:`ValidationError` if the manifest is not spec-conformant."""
    errors = validate_manifest(manifest)
    if errors:
        raise ValidationError(
            f"manifest failed ARD schema validation ({len(errors)} error(s))",
            errors=errors,
        )


def is_valid(manifest: CatalogManifest | dict[str, Any]) -> bool:
    return not validate_manifest(manifest)


def _format_error(error: Any) -> str:
    location = "/".join(str(p) for p in error.absolute_path) or "<root>"
    return f"{location}: {error.message}"


__all__ = [
    "load_schema",
    "spec_version",
    "validate_manifest",
    "assert_valid",
    "is_valid",
]
