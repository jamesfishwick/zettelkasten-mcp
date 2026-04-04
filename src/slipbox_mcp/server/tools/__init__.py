"""MCP tool registrations, split by domain."""


def register_all_tools(server) -> None:
    """Register all MCP tools on the given server."""
    from slipbox_mcp.server.tools.cluster_tools import register_cluster_tools
    from slipbox_mcp.server.tools.search_tools import register_search_tools
    register_cluster_tools(server)
    register_search_tools(server)
