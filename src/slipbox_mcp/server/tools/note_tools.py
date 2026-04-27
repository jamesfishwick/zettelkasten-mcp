"""Note CRUD tools."""
import logging
from typing import Optional

from slipbox_mcp.models.schema import NoteType
from slipbox_mcp.utils import format_tags, parse_refs, parse_tags

logger = logging.getLogger(__name__)


def register_note_tools(server) -> None:
    """Register note CRUD tools."""
    mcp = server.mcp
    zettel_service = server.zettel_service
    format_error = server.format_error_response

    @mcp.tool(name="slipbox_create_note")
    def slipbox_create_note(
        title: str,
        content: str,
        note_type: str = "permanent",
        tags: Optional[str] = None,
        references: Optional[str] = None
    ) -> str:
        """Create a new atomic Zettelkasten note.

        Each note should contain exactly one idea. After creating, immediately
        link to related notes using slipbox_create_link.

        Note Types:
        - fleeting: Quick captures, unprocessed thoughts (process within 24-48 hours)
        - literature: Ideas extracted from sources. REQUIRES at least one entry
          in references (citation or URL). If you don't yet have the citation,
          use 'fleeting' as a staging type and promote to 'literature' once
          the source is attached.
        - permanent: Refined ideas in your own words (the core of your Zettelkasten)
        - structure: Maps organizing 7-15 related notes on a topic
        - hub: Entry points into major knowledge domains

        Best Practices:
        - Title should express the idea in brief (understandable without reading content)
        - Content should be 3-7 paragraphs, enough to stand alone
        - Use 2-5 specific tags; prefer existing tags when they fit
        - Search first (slipbox_search_notes) to avoid duplicating existing notes

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

            tag_list = parse_tags(tags)
            ref_list = parse_refs(references)

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

    @mcp.tool(name="slipbox_get_note")
    def slipbox_get_note(identifier: str) -> str:
        """Retrieve a note by ID or title.

        Returns full note content including metadata, tags, and links.
        Use this to read note contents before creating links or updates.

        Args:
            identifier: Either the note ID (e.g. "20251217T172432480464000") or exact title
        """
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
                result += f"Tags: {format_tags(note.tags)}\n"
            if note.references:
                result += "References:\n"
                for ref in note.references:
                    result += f"  - {ref}\n"
            result += f"\n{note.content}\n"
            return result
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="slipbox_update_note")
    def slipbox_update_note(
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

        Constraint: notes with note_type='literature' must have at least one
        reference. If you are promoting a note to 'literature', pass the
        citation in references in the same call.

        Args:
            note_id: The ID of the note to update
            title: New title (optional)
            content: New content (optional)
            note_type: New type: fleeting/literature/permanent/structure/hub (optional)
            tags: New comma-separated tags, or empty string to clear (optional)
            references: New newline-separated citations, or empty string to clear (optional)
        """
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
                tag_list = parse_tags(tags)

            ref_list = parse_refs(references) if references is not None else None

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

    @mcp.tool(name="slipbox_delete_note")
    def slipbox_delete_note(note_id: str) -> str:
        """Delete a note permanently.

        Warning: This also removes all links to and from this note.
        Consider updating note_type to "fleeting" instead if uncertain.

        Args:
            note_id: The ID of the note to delete
        """
        try:
            note = zettel_service.get_note(note_id)
            if not note:
                return f"Note not found: {note_id}"

            zettel_service.delete_note(str(note_id))
            return f"Note deleted successfully: {note_id}"
        except Exception as e:
            return format_error(e)
