from ardkit.adapters import from_ag2_agent, from_fastmcp, from_mcp_server, mcp_tool_names
from ardkit.media_types import A2A_AGENT_CARD, MCP_SERVER_CARD


class _FakeTool:
    def __init__(self, name):
        self.name = name


class _FakeToolManager:
    def __init__(self, names):
        self._names = names

    def list_tools(self):
        return [_FakeTool(n) for n in self._names]


class _FakeMcpServer:
    def __init__(self, name, tools):
        self.name = name
        self._tool_manager = _FakeToolManager(tools)


def test_mcp_tool_names_introspection():
    server = _FakeMcpServer("Acme", ["agents.list", "voices.list"])
    assert mcp_tool_names(server) == ["agents.list", "voices.list"]


def test_from_mcp_server_builds_entry_with_capabilities():
    server = _FakeMcpServer("Acme MCP", ["agents.list", "campaigns.create"])
    entry = from_mcp_server(
        server,
        url="https://acme.com/api/mcp",
        publisher="acme.com",
        representative_queries=["list my agents", "create a campaign"],
    )
    assert entry.type == MCP_SERVER_CARD
    assert entry.identifier == "urn:air:acme.com:mcp:acme-mcp"
    assert entry.capabilities == ["agents.list", "campaigns.create"]
    assert entry.url == "https://acme.com/api/mcp"


def test_from_fastmcp_alias():
    server = _FakeMcpServer("Tools", ["t1"])
    entry = from_fastmcp(server, url="https://x.com/mcp", publisher="x.com")
    assert entry.capabilities == ["t1"]


class _FakeAgent:
    def __init__(self, name, description):
        self.name = name
        self.description = description


def test_from_ag2_agent():
    agent = _FakeAgent("Voice Campaigner", "Runs AI voice call campaigns.")
    entry = from_ag2_agent(
        agent,
        url="https://acme.com/a2a/voice",
        publisher="acme.com",
        representative_queries=["call my leads", "run a voice campaign"],
    )
    assert entry.type == A2A_AGENT_CARD
    assert entry.identifier == "urn:air:acme.com:agent:voice-campaigner"
    assert entry.description == "Runs AI voice call campaigns."
