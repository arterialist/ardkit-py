import json
from pathlib import Path

import pytest

from ardkit import Catalog
from ardkit.errors import ValidationError
from ardkit.validation import assert_valid, is_valid, spec_version, validate_manifest

DATA = Path(__file__).parent / "data"


def test_spec_version_is_1_0():
    assert spec_version() == "1.0"


def test_builder_output_is_conformant():
    cat = Catalog(host="Acme AI", publisher="acme.com", identifier="did:web:acme.com")
    cat.add_mcp_server(
        name="Billing",
        url="https://acme.com/mcp",
        capabilities=["create_invoice"],
        representative_queries=["create an invoice", "list invoices"],
    )
    errors = validate_manifest(cat.to_manifest())
    assert errors == [], errors
    assert is_valid(cat.to_dict())


@pytest.mark.parametrize("fixture", ["spec-basic.json", "spec-fda-ndc.json"])
def test_spec_examples_conform(fixture):
    data = json.loads((DATA / fixture).read_text("utf-8"))
    assert validate_manifest(data) == []


def test_invalid_manifest_reports_errors():
    bad = {
        "specVersion": "1.0",
        "entries": [
            {
                "identifier": "urn:air:acme.com:mcp:x",
                "displayName": "X",
                "type": "application/mcp-server-card+json",
                # neither url nor data -> oneOf violation
            }
        ],
    }
    errors = validate_manifest(bad)
    assert errors
    with pytest.raises(ValidationError):
        assert_valid(bad)
