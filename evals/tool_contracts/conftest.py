"""Fixtures for deterministic tool contract tests."""
import pytest

from slipbox_mcp.server.mcp_server import ZettelkastenMcpServer


def extract_note_id(result: str) -> str:
    """Extract note ID from tool output like 'Note created successfully with ID: XXX'."""
    return result.split("ID: ")[1].strip()


@pytest.fixture
def server(test_config):
    """MCP server wired to the isolated test database via test_config."""
    return ZettelkastenMcpServer()


@pytest.fixture
def tool(server):
    """Return a helper that resolves a tool function by registered name."""
    def _get(name: str):
        # NOTE: _tool_manager is a private FastMCP API; pin mcp version if this breaks
        return server.mcp._tool_manager.get_tool(name).fn
    return _get
