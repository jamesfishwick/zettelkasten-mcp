"""Search and discovery tools."""
import logging
from datetime import datetime
from typing import Optional

from slipbox_mcp.models.schema import NoteType
from slipbox_mcp.utils import content_preview, format_tags, parse_tags

logger = logging.getLogger(__name__)


def register_search_tools(server) -> None:
    """Register search-related MCP tools."""
    mcp = server.mcp
    search_service = server.search_service
    zettel_service = server.zettel_service
    format_error = server.format_error_response

    @mcp.tool(name="slipbox_search_notes")
    def slipbox_search_notes(
        query: Optional[str] = None,
        tags: Optional[str] = None,
        note_type: Optional[str] = None,
        limit: int = 10
    ) -> str:
        """Search for notes by text, tags, or type.

        Searches across titles and content. Combine parameters for precise filtering.

        Examples:
        - Search by topic: query="poetry revision"
        - Filter by tag: tags="craft,poetry"
        - Find structure notes: note_type="structure"
        - Combined: query="metaphor" tags="poetry" limit=5

        Args:
            query: Text to search in titles and content (optional)
            tags: Comma-separated tags to filter by, e.g. "poetry,craft" (optional)
            note_type: Filter by type: fleeting/literature/permanent/structure/hub (optional)
            limit: Maximum results to return (default: 10)
        """
        try:
            tag_list = parse_tags(tags) if tags is not None else None

            note_type_enum = None
            if note_type:
                try:
                    note_type_enum = NoteType(note_type.lower())
                except ValueError:
                    return f"Invalid note type: {note_type}. Valid types are: {', '.join(t.value for t in NoteType)}"

            results = search_service.search_combined(
                query_text=query,
                tags=tag_list,
                note_type=note_type_enum
            )

            results = results[:limit]
            if not results:
                return "No matching notes found."

            output = f"Found {len(results)} matching notes:\n\n"
            for i, result in enumerate(results, 1):
                note = result.note
                output += f"{i}. {note.title} (ID: {note.id})\n"
                if note.tags:
                    output += f"   Tags: {format_tags(note.tags)}\n"
                output += f"   Created: {note.created_at.strftime('%Y-%m-%d')}\n"
                output += f"   Preview: {content_preview(note.content)}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="slipbox_find_similar_notes")
    def slipbox_find_similar_notes(
        note_id: str,
        threshold: float = 0.3,
        limit: int = 5
    ) -> str:
        """Find notes similar to a given note.

        Similarity is based on shared tags, common links, and content overlap.
        Useful for discovering connections you might have missed.

        Args:
            note_id: ID of the reference note
            threshold: Minimum similarity score 0.0-1.0 (default: 0.3)
            limit: Maximum results (default: 5)
        """
        try:
            if not 0.0 <= threshold <= 1.0:
                logger.warning("slipbox_find_similar_notes: threshold %r out of range [0.0, 1.0]", threshold)
                return "Error: threshold must be between 0.0 and 1.0."
            if limit <= 0:
                logger.warning("slipbox_find_similar_notes: limit %r must be a positive integer", limit)
                return "Error: limit must be a positive integer."
            similar_notes = zettel_service.find_similar_notes(str(note_id), threshold)
            similar_notes = similar_notes[:limit]
            if not similar_notes:
                return f"No similar notes found for {note_id} with threshold {threshold}."

            output = f"Found {len(similar_notes)} similar notes for {note_id}:\n\n"
            for i, (note, similarity) in enumerate(similar_notes, 1):
                output += f"{i}. {note.title} (ID: {note.id})\n"
                output += f"   Similarity: {similarity:.2f}\n"
                if note.tags:
                    output += f"   Tags: {format_tags(note.tags)}\n"
                output += f"   Preview: {content_preview(note.content)}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="slipbox_find_central_notes")
    def slipbox_find_central_notes(limit: int = 10) -> str:
        """Find the most connected notes in the Zettelkasten.

        Central notes have the most incoming and outgoing links, making them
        key hubs in your knowledge network. Good candidates for hub notes.

        Args:
            limit: Maximum results (default: 10)
        """
        try:
            if limit <= 0:
                logger.warning("slipbox_find_central_notes: limit %r must be a positive integer", limit)
                return "Error: limit must be a positive integer."
            central_notes = search_service.find_central_notes(limit)
            if not central_notes:
                return "No notes found with connections."

            output = "Central notes in the Zettelkasten (most connected):\n\n"
            for i, (note, connection_count) in enumerate(central_notes, 1):
                output += f"{i}. {note.title} (ID: {note.id})\n"
                output += f"   Connections: {connection_count}\n"
                if note.tags:
                    output += f"   Tags: {format_tags(note.tags)}\n"
                output += f"   Preview: {content_preview(note.content)}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="slipbox_find_orphaned_notes")
    def slipbox_find_orphaned_notes() -> str:
        """Find notes with no connections to other notes.

        Orphaned notes represent unintegrated knowledge. Review these periodically
        to either link them to existing notes or identify candidates for deletion.
        """
        try:
            orphans = search_service.find_orphaned_notes()
            if not orphans:
                return "No orphaned notes found."

            output = f"Found {len(orphans)} orphaned notes:\n\n"
            for i, note in enumerate(orphans, 1):
                output += f"{i}. {note.title} (ID: {note.id})\n"
                if note.tags:
                    output += f"   Tags: {format_tags(note.tags)}\n"
                output += f"   Preview: {content_preview(note.content)}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="slipbox_list_notes_by_date")
    def slipbox_list_notes_by_date(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_updated: bool = False,
        limit: int = 10
    ) -> str:
        """List notes by creation or update date.

        Useful for reviewing recent work or finding notes from a specific period.

        Args:
            start_date: Start date in ISO format YYYY-MM-DD (optional)
            end_date: End date in ISO format YYYY-MM-DD (optional)
            use_updated: If true, filter by updated_at instead of created_at (default: false)
            limit: Maximum results (default: 10)
        """
        try:
            start_datetime = None
            if start_date:
                start_datetime = datetime.fromisoformat(f"{start_date}T00:00:00")
            end_datetime = None
            if end_date:
                end_datetime = datetime.fromisoformat(f"{end_date}T23:59:59")

            notes = search_service.find_notes_by_date_range(
                start_date=start_datetime,
                end_date=end_datetime,
                use_updated=use_updated
            )

            notes = notes[:limit]
            if not notes:
                date_type = "updated" if use_updated else "created"
                date_range = ""
                if start_date and end_date:
                    date_range = f" between {start_date} and {end_date}"
                elif start_date:
                    date_range = f" after {start_date}"
                elif end_date:
                    date_range = f" before {end_date}"
                return f"No notes found {date_type}{date_range}."

            date_type = "updated" if use_updated else "created"
            output = f"Notes {date_type}"
            if start_date or end_date:
                if start_date and end_date:
                    output += f" between {start_date} and {end_date}"
                elif start_date:
                    output += f" after {start_date}"
                elif end_date:
                    output += f" before {end_date}"
            output += f" (showing {len(notes)} results):\n\n"
            for i, note in enumerate(notes, 1):
                date = note.updated_at if use_updated else note.created_at
                output += f"{i}. {note.title} (ID: {note.id})\n"
                output += f"   {date_type.capitalize()}: {date.strftime('%Y-%m-%d %H:%M')}\n"
                if note.tags:
                    output += f"   Tags: {format_tags(note.tags)}\n"
                output += f"   Preview: {content_preview(note.content)}\n\n"
            return output
        except ValueError as e:
            logger.error("Date parsing error: %s", e)
            return f"Error parsing date: {str(e)}"
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="slipbox_rebuild_index")
    def slipbox_rebuild_index() -> str:
        """Rebuild the database index from markdown files.

        Use this if notes were edited outside the MCP server or if the
        database seems out of sync with the filesystem.
        """
        try:
            note_count_before = len(zettel_service.get_all_notes())
            zettel_service.rebuild_index()
            note_count_after = len(zettel_service.get_all_notes())
            return (
                f"Database index rebuilt successfully.\n"
                f"Notes processed: {note_count_after}\n"
                f"Change in note count: {note_count_after - note_count_before}"
            )
        except Exception as e:
            logger.error("Failed to rebuild index: %s", e, exc_info=True)
            return format_error(e)
