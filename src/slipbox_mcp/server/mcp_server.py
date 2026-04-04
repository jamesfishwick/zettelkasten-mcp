"""MCP server implementation for the Zettelkasten."""
import logging
import uuid
from datetime import datetime
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from slipbox_mcp.config import config
from slipbox_mcp.models.schema import NoteType
from slipbox_mcp.services.search_service import SearchService
from slipbox_mcp.services.cluster_service import ClusterService
from slipbox_mcp.services.zettel_service import ZettelService

logger = logging.getLogger(__name__)


def _parse_tags(tags: Optional[str]) -> List[str]:
    """Split a comma-separated tag string into a list of stripped tag names."""
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def _parse_refs(references: Optional[str]) -> List[str]:
    """Split a newline-separated references string into a list of stripped entries."""
    if not references:
        return []
    return [r.strip() for r in references.split("\n") if r.strip()]


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
        from slipbox_mcp.server.tools.cluster_tools import register_cluster_tools
        from slipbox_mcp.server.tools.link_tools import register_link_tools
        from slipbox_mcp.server.tools.search_tools import register_search_tools
        register_cluster_tools(self)
        register_link_tools(self)
        register_search_tools(self)

        @self.mcp.tool(name="zk_create_note")
        def zk_create_note(
            title: str,
            content: str,
            note_type: str = "permanent",
            tags: Optional[str] = None,
            references: Optional[str] = None
        ) -> str:
            """Create a new atomic Zettelkasten note.

            Each note should contain exactly one idea. After creating, immediately
            link to related notes using zk_create_link.

            Note Types:
            - fleeting: Quick captures, unprocessed thoughts (process within 24-48 hours)
            - literature: Ideas extracted from sources (always include citation in references)
            - permanent: Refined ideas in your own words (the core of your Zettelkasten)
            - structure: Maps organizing 7-15 related notes on a topic
            - hub: Entry points into major knowledge domains

            Best Practices:
            - Title should express the idea in brief (understandable without reading content)
            - Content should be 3-7 paragraphs, enough to stand alone
            - Use 2-5 specific tags; prefer existing tags when they fit
            - Search first (zk_search_notes) to avoid duplicating existing notes

            Args:
                title: Concise title expressing the core idea
                content: Full note content in markdown
                note_type: One of fleeting/literature/permanent/structure/hub (default: permanent)
                tags: Comma-separated tags, e.g. "poetry,revision,craft"
                references: Newline-separated citations to external sources (e.g. "Ahrens, S. (2017). How to Take Smart Notes.\nhttps://zettelkasten.de")
            """
            try:
                try:
                    note_type_enum = NoteType(note_type.lower())
                except ValueError:
                    return f"Invalid note type: {note_type}. Valid types are: {', '.join(t.value for t in NoteType)}"

                tag_list = _parse_tags(tags)
                ref_list = _parse_refs(references)

                note = self.zettel_service.create_note(
                    title=title,
                    content=content,
                    note_type=note_type_enum,
                    tags=tag_list,
                    references=ref_list,
                )
                return f"Note created successfully with ID: {note.id}"
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_get_note")
        def zk_get_note(identifier: str) -> str:
            """Retrieve a note by ID or title.

            Returns full note content including metadata, tags, and links.
            Use this to read note contents before creating links or updates.

            Args:
                identifier: Either the note ID (e.g. "20251217T172432480464000") or exact title
            """
            try:
                identifier = str(identifier)
                note = self.zettel_service.get_note(identifier)
                if not note:
                    note = self.zettel_service.get_note_by_title(identifier)
                if not note:
                    return f"Note not found: {identifier}"

                result = f"# {note.title}\n"
                result += f"ID: {note.id}\n"
                result += f"Type: {note.note_type.value}\n"
                result += f"Created: {note.created_at.isoformat()}\n"
                result += f"Updated: {note.updated_at.isoformat()}\n"
                if note.tags:
                    result += f"Tags: {', '.join(tag.name for tag in note.tags)}\n"
                if note.references:
                    result += "References:\n"
                    for ref in note.references:
                        result += f"  - {ref}\n"
                result += f"\n{note.content}\n"
                return result
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_update_note")
        def zk_update_note(
            note_id: str,
            title: Optional[str] = None,
            content: Optional[str] = None,
            note_type: Optional[str] = None,
            tags: Optional[str] = None,
            references: Optional[str] = None
        ) -> str:
            """Update an existing note.

            Only provided fields are updated; omitted fields remain unchanged.
            Pass empty string for tags to clear all tags.
            Pass empty string for references to clear all references.

            Args:
                note_id: The ID of the note to update
                title: New title (optional)
                content: New content (optional)
                note_type: New type: fleeting/literature/permanent/structure/hub (optional)
                tags: New comma-separated tags, or empty string to clear (optional)
                references: New newline-separated citations, or empty string to clear (optional)
            """
            try:
                note = self.zettel_service.get_note(str(note_id))
                if not note:
                    return f"Note not found: {note_id}"

                note_type_enum = None
                if note_type:
                    try:
                        note_type_enum = NoteType(note_type.lower())
                    except ValueError:
                        return f"Invalid note type: {note_type}. Valid types are: {', '.join(t.value for t in NoteType)}"

                tag_list = None
                if tags is not None:  # Allow empty string to clear tags
                    tag_list = _parse_tags(tags)

                ref_list = _parse_refs(references) if references is not None else None

                updated_note = self.zettel_service.update_note(
                    note_id=note_id,
                    title=title,
                    content=content,
                    note_type=note_type_enum,
                    tags=tag_list,
                    references=ref_list
                )
                return f"Note updated successfully: {updated_note.id}"
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_delete_note")
        def zk_delete_note(note_id: str) -> str:
            """Delete a note permanently.

            Warning: This also removes all links to and from this note.
            Consider updating note_type to "fleeting" instead if uncertain.

            Args:
                note_id: The ID of the note to delete
            """
            try:
                note = self.zettel_service.get_note(note_id)
                if not note:
                    return f"Note not found: {note_id}"

                self.zettel_service.delete_note(str(note_id))
                return f"Note deleted successfully: {note_id}"
            except Exception as e:
                return self.format_error_response(e)


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
