"""Search and discovery tools."""
import logging
from datetime import datetime
from typing import Optional

from slipbox_mcp.models.schema import NoteType
from slipbox_mcp.server.descriptions import (
    ZK_FIND_CENTRAL_NOTES,
    ZK_FIND_ORPHANED_NOTES,
    ZK_FIND_SIMILAR_NOTES,
    ZK_LIST_NOTES_BY_DATE,
    ZK_REBUILD_INDEX,
    ZK_SEARCH_NOTES,
)

logger = logging.getLogger(__name__)


def _parse_tags(tags: Optional[str]):
    """Split a comma-separated tag string into a list of stripped tag names."""
    if not tags:
        return []
    return [t.strip() for t in tags.split(",") if t.strip()]


def register_search_tools(server) -> None:
    """Register search-related MCP tools."""
    mcp = server.mcp
    search_service = server.search_service
    zettel_service = server.zettel_service
    format_error = server.format_error_response

    @mcp.tool(name="zk_search_notes", description=ZK_SEARCH_NOTES)
    def zk_search_notes(
        query: Optional[str] = None,
        tags: Optional[str] = None,
        note_type: Optional[str] = None,
        limit: int = 10
    ) -> str:
        try:
            tag_list = _parse_tags(tags) if tags is not None else None

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
                    output += f"   Tags: {', '.join(tag.name for tag in note.tags)}\n"
                output += f"   Created: {note.created_at.strftime('%Y-%m-%d')}\n"
                content_preview = note.content[:150].replace("\n", " ")
                if len(note.content) > 150:
                    content_preview += "..."
                output += f"   Preview: {content_preview}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_find_similar_notes", description=ZK_FIND_SIMILAR_NOTES)
    def zk_find_similar_notes(
        note_id: str,
        threshold: float = 0.3,
        limit: int = 5
    ) -> str:
        try:
            if not 0.0 <= threshold <= 1.0:
                logger.warning("zk_find_similar_notes: threshold %r out of range [0.0, 1.0]", threshold)
                return "Error: threshold must be between 0.0 and 1.0."
            if limit <= 0:
                logger.warning("zk_find_similar_notes: limit %r must be a positive integer", limit)
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
                    output += f"   Tags: {', '.join(tag.name for tag in note.tags)}\n"
                content_preview = note.content[:100].replace("\n", " ")
                if len(note.content) > 100:
                    content_preview += "..."
                output += f"   Preview: {content_preview}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_find_central_notes", description=ZK_FIND_CENTRAL_NOTES)
    def zk_find_central_notes(limit: int = 10) -> str:
        try:
            if limit <= 0:
                logger.warning("zk_find_central_notes: limit %r must be a positive integer", limit)
                return "Error: limit must be a positive integer."
            central_notes = search_service.find_central_notes(limit)
            if not central_notes:
                return "No notes found with connections."

            output = "Central notes in the Zettelkasten (most connected):\n\n"
            for i, (note, connection_count) in enumerate(central_notes, 1):
                output += f"{i}. {note.title} (ID: {note.id})\n"
                output += f"   Connections: {connection_count}\n"
                if note.tags:
                    output += f"   Tags: {', '.join(tag.name for tag in note.tags)}\n"
                content_preview = note.content[:100].replace("\n", " ")
                if len(note.content) > 100:
                    content_preview += "..."
                output += f"   Preview: {content_preview}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_find_orphaned_notes", description=ZK_FIND_ORPHANED_NOTES)
    def zk_find_orphaned_notes() -> str:
        try:
            orphans = search_service.find_orphaned_notes()
            if not orphans:
                return "No orphaned notes found."

            output = f"Found {len(orphans)} orphaned notes:\n\n"
            for i, note in enumerate(orphans, 1):
                output += f"{i}. {note.title} (ID: {note.id})\n"
                if note.tags:
                    output += f"   Tags: {', '.join(tag.name for tag in note.tags)}\n"
                content_preview = note.content[:100].replace("\n", " ")
                if len(note.content) > 100:
                    content_preview += "..."
                output += f"   Preview: {content_preview}\n\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_list_notes_by_date", description=ZK_LIST_NOTES_BY_DATE)
    def zk_list_notes_by_date(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_updated: bool = False,
        limit: int = 10
    ) -> str:
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
                    output += f"   Tags: {', '.join(tag.name for tag in note.tags)}\n"
                content_preview = note.content[:100].replace("\n", " ")
                if len(note.content) > 100:
                    content_preview += "..."
                output += f"   Preview: {content_preview}\n\n"
            return output
        except ValueError as e:
            logger.error("Date parsing error: %s", e)
            return f"Error parsing date: {str(e)}"
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_rebuild_index", description=ZK_REBUILD_INDEX)
    def zk_rebuild_index() -> str:
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
