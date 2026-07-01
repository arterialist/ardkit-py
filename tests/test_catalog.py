import pytest

from ardkit import Catalog, make_urn, slugify
from ardkit.media_types import A2A_AGENT_CARD, MCP_SERVER_CARD


def test_make_urn_and_slugify():
    assert slugify("Voice Campaigns!") == "voice-campaigns"
    assert (
        make_urn("acme.com", "agent", "Voice Campaigns") == "urn:air:acme.com:agent:voice-campaigns"
    )


def test_make_urn_requires_segment():
    with pytest.raises(ValueError):
        make_urn("acme.com")


def test_builder_mints_urns_from_publisher():
    cat = Catalog(host="Acme AI", publisher="acme.com")
    mcp = cat.add_mcp_server(
        name="Billing",
        url="https://acme.com/mcp",
        capabilities=["create_invoice"],
        representative_queries=["create an invoice", "list invoices"],
    )
    agent = cat.add_a2a_agent(
        name="WhatsApp Campaigns",
        url="https://acme.com/a2a/whatsapp",
        representative_queries=["run a whatsapp campaign", "message my leads"],
    )
    assert mcp.identifier == "urn:air:acme.com:mcp:billing"
    assert mcp.type == MCP_SERVER_CARD
    assert agent.identifier == "urn:air:acme.com:agent:whatsapp-campaigns"
    assert agent.type == A2A_AGENT_CARD

    manifest = cat.to_manifest()
    assert manifest.host is not None
    assert manifest.host.display_name == "Acme AI"
    assert len(manifest.entries) == 2


def test_publisher_inferred_from_did_web_identifier():
    cat = Catalog(host="Acme", identifier="did:web:acme.com")
    entry = cat.add_skill(name="Translate", url="https://acme.com/skill")
    assert entry.identifier == "urn:air:acme.com:skill:translate"


def test_explicit_identifier_skips_minting():
    cat = Catalog(host="Acme")
    entry = cat.add_entry(
        identifier="urn:air:acme.com:custom:thing",
        display_name="Thing",
        type="application/x-custom",
        url="https://acme.com/thing",
    )
    assert entry.identifier == "urn:air:acme.com:custom:thing"


def test_touch_sets_updated_at():
    cat = Catalog(host="Acme", publisher="acme.com")
    cat.add_skill(name="Translate", url="https://acme.com/skill")
    manifest = cat.to_manifest(touch=True)
    assert manifest.entries[0].updated_at is not None
