"""MCP server implementation for the Zettelkasten."""
import logging
import uuid
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from slipbox_mcp.config import config
from slipbox_mcp.services.search_service import SearchService
from slipbox_mcp.services.cluster_service import ClusterService
from slipbox_mcp.services.zettel_service import ZettelService

logger = logging.getLogger(__name__)


class ZettelkastenMcpServer:
    """MCP server for Zettelkasten."""
    def __init__(self):
        self.mcp = FastMCP(
            config.server_name
        )
        self.zettel_service = ZettelService()
        self.search_service = SearchService(self.zettel_service)
        self.cluster_service = ClusterService(self.zettel_service)
        self.initialize()
        self._register_tools()
        self._register_resources()
        self._register_prompts()

    def initialize(self) -> None:
        """Initialize services."""
        self._maybe_refresh_clusters()
        logger.info("Zettelkasten MCP server initialized")

    def _maybe_refresh_clusters(self) -> None:
        """Refresh cluster analysis if the report is stale (>24h old)."""
        try:
            report = self.cluster_service.load_report()

            should_refresh = False
            if not report:
                should_refresh = True
            else:
                age_hours = (datetime.now() - report.generated_at).total_seconds() / 3600
                should_refresh = age_hours > 24

            if should_refresh:
                logger.info("Refreshing stale cluster report...")
                new_report = self.cluster_service.detect_clusters()
                # Preserve dismissed clusters from old report
                if report:
                    new_report.dismissed_cluster_ids = report.dismissed_cluster_ids
                self.cluster_service.save_report(new_report)
                logger.info("Cluster report refreshed: %s", new_report.stats)
        except Exception as e:
            logger.warning("Failed to refresh clusters on startup: %s", e)

    def format_error_response(self, error: Exception) -> str:
        """Format an error response for MCP tool callers."""
        error_id = str(uuid.uuid4())[:8]

        if isinstance(error, ValueError):
            logger.error("Validation error [%s]: %s", error_id, error)
            return f"Error: {error}"
        elif isinstance(error, (IOError, OSError)):
            logger.error("File system error [%s]: %s", error_id, error, exc_info=True)
            return f"Error: {error}"
        else:
            logger.error("Unexpected error [%s]: %s", error_id, error, exc_info=True)
            return f"Error: {error}"

    def _register_tools(self) -> None:
        """Register MCP tools."""
        from slipbox_mcp.server.tools import register_all_tools
        register_all_tools(self)

    def _register_resources(self) -> None:
        from slipbox_mcp.server.resources import register_resources
        register_resources(self)

    def _register_prompts(self) -> None:
        """Register MCP prompts for knowledge workflows."""
        from slipbox_mcp.server.prompts import register_prompts
        register_prompts(self)

    def run(self) -> None:
        """Run the MCP server."""
        self.mcp.run()
