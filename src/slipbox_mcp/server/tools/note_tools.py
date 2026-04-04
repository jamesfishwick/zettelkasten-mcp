"""Note CRUD tools."""
import logging
from typing import List, Optional

from slipbox_mcp.models.schema import NoteType
from slipbox_mcp.server.descriptions import (
    ZK_CREATE_NOTE,
    ZK_DELETE_NOTE,
    ZK_GET_NOTE,
    ZK_UPDATE_NOTE,
)

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


def register_note_tools(server) -> None:
    """Register note CRUD tools."""
    mcp = server.mcp
    zettel_service = server.zettel_service
    format_error = server.format_error_response

    @mcp.tool(name="zk_create_note", description=ZK_CREATE_NOTE)
    def zk_create_note(
        title: str,
        content: str,
        note_type: str = "permanent",
        tags: Optional[str] = None,
        references: Optional[str] = None
    ) -> str:
        try:
            try:
                note_type_enum = NoteType(note_type.lower())
            except ValueError:
                return f"Invalid note type: {note_type}. Valid types are: {', '.join(t.value for t in NoteType)}"

            tag_list = _parse_tags(tags)
            ref_list = _parse_refs(references)

            note = zettel_service.create_note(
                title=title,
                content=content,
                note_type=note_type_enum,
                tags=tag_list,
                references=ref_list,
            )
            return f"Note created successfully with ID: {note.id}"
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_get_note", description=ZK_GET_NOTE)
    def zk_get_note(identifier: str) -> str:
        try:
            identifier = str(identifier)
            note = zettel_service.get_note(identifier)
            if not note:
                note = zettel_service.get_note_by_title(identifier)
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
            return format_error(e)

    @mcp.tool(name="zk_update_note", description=ZK_UPDATE_NOTE)
    def zk_update_note(
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        note_type: Optional[str] = None,
        tags: Optional[str] = None,
        references: Optional[str] = None
    ) -> str:
        try:
            note = zettel_service.get_note(str(note_id))
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

            updated_note = zettel_service.update_note(
                note_id=note_id,
                title=title,
                content=content,
                note_type=note_type_enum,
                tags=tag_list,
                references=ref_list
            )
            return f"Note updated successfully: {updated_note.id}"
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_delete_note", description=ZK_DELETE_NOTE)
    def zk_delete_note(note_id: str) -> str:
        try:
            note = zettel_service.get_note(note_id)
            if not note:
                return f"Note not found: {note_id}"

            zettel_service.delete_note(str(note_id))
            return f"Note deleted successfully: {note_id}"
        except Exception as e:
            return format_error(e)
