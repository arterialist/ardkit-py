import pytest
from pydantic import ValidationError

from ardkit import CatalogEntry, CatalogManifest, HostInfo
from ardkit.media_types import MCP_SERVER_CARD


def test_entry_serialises_camelcase():
    entry = CatalogEntry(
        identifier="urn:air:acme.com:mcp:billing",
        display_name="Billing",
        type=MCP_SERVER_CARD,
        url="https://acme.com/mcp",
        representative_queries=["create an invoice", "list invoices"],
    )
    dumped = CatalogManifest(host=HostInfo(display_name="Acme"), entries=[entry]).to_dict()
    assert dumped["specVersion"] == "1.0"
    assert dumped["host"]["displayName"] == "Acme"
    item = dumped["entries"][0]
    assert item["displayName"] == "Billing"
    assert item["representativeQueries"] == ["create an invoice", "list invoices"]
    assert "url" in item and "data" not in item


def test_entry_requires_url_xor_data():
    with pytest.raises(ValidationError):
        CatalogEntry(identifier="urn:air:a.com:x:y", display_name="x", type="t")  # neither
    with pytest.raises(ValidationError):
        CatalogEntry(
            identifier="urn:air:a.com:x:y",
            display_name="x",
            type="t",
            url="https://a.com",
            data={"k": "v"},
        )  # both


def test_invalid_urn_rejected():
    with pytest.raises(ValidationError):
        CatalogEntry(identifier="not-a-urn", display_name="x", type="t", url="https://a.com")


def test_representative_queries_bounds():
    with pytest.raises(ValidationError):
        CatalogEntry(
            identifier="urn:air:a.com:x:y",
            display_name="x",
            type="t",
            url="https://a.com",
            representative_queries=["only one"],
        )


def test_manifest_round_trip():
    manifest = CatalogManifest.from_dict(
        {
            "specVersion": "1.0",
            "host": {"displayName": "Acme"},
            "entries": [
                {
                    "identifier": "urn:air:acme.com:mcp:billing",
                    "displayName": "Billing",
                    "type": MCP_SERVER_CARD,
                    "url": "https://acme.com/mcp",
                }
            ],
        }
    )
    assert manifest.entries[0].display_name == "Billing"
    assert manifest.to_dict()["entries"][0]["identifier"] == "urn:air:acme.com:mcp:billing"
