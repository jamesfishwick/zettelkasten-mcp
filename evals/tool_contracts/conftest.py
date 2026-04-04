"""Fixtures for deterministic tool contract tests."""
import pytest

from slipbox_mcp.server.mcp_server import ZettelkastenMcpServer


@pytest.fixture
def server(test_config):
    """MCP server wired to the isolated test database via test_config."""
    return ZettelkastenMcpServer()


@pytest.fixture
def tool(server):
    """Return a helper that resolves a tool function by registered name."""
    def _get(name: str):
        return server.mcp._tool_manager.get_tool(name).fn
    return _get
