from ardkit import agentmap_line, augment_robots, dns_records, link_tag, well_known_url


def test_well_known_url():
    assert well_known_url("https://acme.com/") == "https://acme.com/.well-known/ai-catalog.json"


def test_agentmap_and_link():
    url = "https://acme.com/.well-known/ai-catalog.json"
    assert agentmap_line(url) == f"Agentmap: {url}"
    assert link_tag(url) == f'<link rel="ai-catalog" href="{url}">'


def test_augment_robots_appends_and_is_idempotent():
    url = "https://acme.com/.well-known/ai-catalog.json"
    base = "User-agent: *\nAllow: /"
    once = augment_robots(base, url)
    assert "Agentmap: " + url in once
    twice = augment_robots(once, url)
    assert once.count("Agentmap:") == 1
    assert twice.count("Agentmap:") == 1


def test_augment_robots_from_empty():
    out = augment_robots(None, "https://acme.com/.well-known/ai-catalog.json")
    assert out.strip().startswith("Agentmap:")


def test_dns_records():
    recs = dns_records(
        "acme.com", catalog_url="https://acme.com/c.json", search_url="https://r.acme.com/search"
    )
    assert any("_catalog._agents.acme.com" in r for r in recs)
    assert any("_search._agents.acme.com" in r for r in recs)
