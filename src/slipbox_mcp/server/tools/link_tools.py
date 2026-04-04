"""Link management and tag tools."""
import logging
from typing import Optional

from sqlalchemy import exc as sqlalchemy_exc

from slipbox_mcp.models.schema import LinkType

logger = logging.getLogger(__name__)


def register_link_tools(server) -> None:
    """Register link and tag tools."""
    mcp = server.mcp
    zettel_service = server.zettel_service
    format_error = server.format_error_response

    @mcp.tool(name="zk_create_link")
    def zk_create_link(
        source_id: str,
        target_id: str,
        link_type: str = "reference",
        description: Optional[str] = None,
        bidirectional: bool = False
    ) -> str:
        """Create a semantic link between two notes.

        Links are directional: source -> target. Use bidirectional=true for
        important relationships (automatically creates inverse link type).

        Link Types:
        - reference: Generic "see also" connection
        - extends: Source builds upon target (inverse: extended_by)
        - refines: Source clarifies or improves target (inverse: refined_by)
        - contradicts: Source presents opposing view (inverse: contradicted_by)
        - questions: Source raises questions about target (inverse: questioned_by)
        - supports: Source provides evidence for target (inverse: supported_by)
        - related: Loose thematic connection (symmetric)

        Best Practices:
        - Always add description explaining WHY notes are linked
        - Use bidirectional=true for substantive relationships
        - Create links immediately after creating notes

        Args:
            source_id: ID of the source note (the note doing the linking)
            target_id: ID of the target note (the note being linked to)
            link_type: One of reference/extends/refines/contradicts/questions/supports/related
            description: Brief explanation of the relationship
            bidirectional: If true, creates inverse link from target to source
        """
        try:
            try:
                link_type_enum = LinkType(link_type.lower())
            except ValueError:
                return f"Invalid link type: {link_type}. Valid types are: {', '.join(t.value for t in LinkType)}"

            source_note, target_note = zettel_service.create_link(
                source_id=source_id,
                target_id=target_id,
                link_type=link_type_enum,
                description=description,
                bidirectional=bidirectional
            )
            if bidirectional:
                return f"Bidirectional link created between {source_id} and {target_id}"
            else:
                return f"Link created from {source_id} to {target_id}"
        except (Exception, sqlalchemy_exc.IntegrityError) as e:
            if "UNIQUE constraint failed" in str(e):
                return "A link of this type already exists between these notes. Try a different link type."
            return format_error(e)

    @mcp.tool(name="zk_remove_link")
    def zk_remove_link(
        source_id: str,
        target_id: str,
        bidirectional: bool = False
    ) -> str:
        """Remove a link between two notes.

        Args:
            source_id: ID of the source note
            target_id: ID of the target note
            bidirectional: If true, removes links in both directions
        """
        try:
            source_note, target_note = zettel_service.remove_link(
                source_id=str(source_id),
                target_id=str(target_id),
                bidirectional=bidirectional
            )
            if bidirectional:
                return f"Bidirectional link removed between {source_id} and {target_id}"
            else:
                return f"Link removed from {source_id} to {target_id}"
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_get_linked_notes")
    def zk_get_linked_notes(
        note_id: str,
        direction: str = "both"
    ) -> str:
        """Get notes linked to or from a specific note.

        Use this to explore the knowledge graph around a note.

        Directions:
        - outgoing: Notes this note links TO
        - incoming: Notes that link TO this note
        - both: All connected notes in either direction

        Args:
            note_id: ID of the note to explore from
            direction: One of outgoing/incoming/both (default: both)
        """
        try:
            if direction not in ["outgoing", "incoming", "both"]:
                return f"Invalid direction: {direction}. Use 'outgoing', 'incoming', or 'both'."
            linked_notes = zettel_service.get_linked_notes(str(note_id), direction)
            if not linked_notes:
                return f"No {direction} links found for note {note_id}."
            output = f"Found {len(linked_notes)} {direction} linked notes for {note_id}:\n\n"
            for i, note in enumerate(linked_notes, 1):
                output += f"{i}. {note.title} (ID: {note.id})\n"
                if note.tags:
                    output += f"   Tags: {', '.join(tag.name for tag in note.tags)}\n"
                if direction in ["outgoing", "both"]:
                    source_note = zettel_service.get_note(str(note_id))
                    if source_note:
                        for link in source_note.links:
                            if str(link.target_id) == str(note.id):
                                output += f"   Link type: {link.link_type.value}\n"
                                if link.description:
                                    output += f"   Description: {link.description}\n"
                                break
                if direction in ["incoming", "both"]:
                    for link in note.links:
                        if str(link.target_id) == str(note_id):
                            output += f"   Incoming link type: {link.link_type.value}\n"
                            if link.description:
                                output += f"   Description: {link.description}\n"
                            break
                output += "\n"
            return output
        except Exception as e:
            return format_error(e)

    @mcp.tool(name="zk_get_all_tags")
    def zk_get_all_tags() -> str:
        """Get all tags in the Zettelkasten.

        Returns alphabetically sorted list of all tags.
        Use this to find existing tags before creating new notes
        to maintain tag consistency across your knowledge base.
        """
        try:
            tags = zettel_service.get_all_tags()
            if not tags:
                return "No tags found in the Zettelkasten."

            output = f"Found {len(tags)} tags:\n\n"
            tags.sort(key=lambda t: t.name.lower())
            for i, tag in enumerate(tags, 1):
                output += f"{i}. {tag.name}\n"
            return output
        except Exception as e:
            return format_error(e)
