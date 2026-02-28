"""MCP server implementation for the Zettelkasten."""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import exc as sqlalchemy_exc
from mcp.server.fastmcp import Context, FastMCP
from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.schema import LinkType, Note, NoteType, Tag
from zettelkasten_mcp.services.search_service import SearchService
from zettelkasten_mcp.services.cluster_service import ClusterService
from zettelkasten_mcp.services.zettel_service import ZettelService

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
        self.zettel_service.initialize()
        self.search_service.initialize()
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
                logger.info(f"Cluster report refreshed: {new_report.stats}")
        except Exception as e:
            logger.warning(f"Failed to refresh clusters on startup: {e}")

    def format_error_response(self, error: Exception) -> str:
        """Format an error response for MCP tool callers."""
        error_id = str(uuid.uuid4())[:8]

        if isinstance(error, ValueError):
            logger.error(f"Validation error [{error_id}]: {str(error)}")
            return f"Error: {str(error)}"
        elif isinstance(error, (IOError, OSError)):
            logger.error(f"File system error [{error_id}]: {str(error)}", exc_info=True)
            return f"Error: {str(error)}"
        else:
            logger.error(f"Unexpected error [{error_id}]: {str(error)}", exc_info=True)
            return f"Error: {str(error)}"

    def _register_tools(self) -> None:
        """Register MCP tools."""
        @self.mcp.tool(name="zk_create_note")
        def zk_create_note(
            title: str, 
            content: str, 
            note_type: str = "permanent",
            tags: Optional[str] = None
        ) -> str:
            """Create a new atomic Zettelkasten note.

            Each note should contain exactly one idea. After creating, immediately
            link to related notes using zk_create_link.

            Note Types:
            - fleeting: Quick captures, unprocessed thoughts (process within 24-48 hours)
            - literature: Ideas extracted from sources (always include citation in content)
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
            """
            try:
                try:
                    note_type_enum = NoteType(note_type.lower())
                except ValueError:
                    return f"Invalid note type: {note_type}. Valid types are: {', '.join(t.value for t in NoteType)}"

                tag_list = []
                if tags:
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                note = self.zettel_service.create_note(
                    title=title,
                    content=content,
                    note_type=note_type_enum,
                    tags=tag_list,
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
            tags: Optional[str] = None
        ) -> str:
            """Update an existing note.

            Only provided fields are updated; omitted fields remain unchanged.
            Pass empty string for tags to clear all tags.

            Args:
                note_id: The ID of the note to update
                title: New title (optional)
                content: New content (optional)
                note_type: New type: fleeting/literature/permanent/structure/hub (optional)
                tags: New comma-separated tags, or empty string to clear (optional)
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
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                updated_note = self.zettel_service.update_note(
                    note_id=note_id,
                    title=title,
                    content=content,
                    note_type=note_type_enum,
                    tags=tag_list
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

        @self.mcp.tool(name="zk_create_link")
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
                    source_id_str = str(source_id)
                    target_id_str = str(target_id)
                    link_type_enum = LinkType(link_type.lower())
                except ValueError:
                    return f"Invalid link type: {link_type}. Valid types are: {', '.join(t.value for t in LinkType)}"

                source_note, target_note = self.zettel_service.create_link(
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
                    return f"A link of this type already exists between these notes. Try a different link type."
                return self.format_error_response(e)
        self.zk_create_link = zk_create_link

        @self.mcp.tool(name="zk_remove_link")
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
                source_note, target_note = self.zettel_service.remove_link(
                    source_id=str(source_id),
                    target_id=str(target_id),
                    bidirectional=bidirectional
                )
                if bidirectional:
                    return f"Bidirectional link removed between {source_id} and {target_id}"
                else:
                    return f"Link removed from {source_id} to {target_id}"
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_search_notes")
        def zk_search_notes(
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
                tag_list = None
                if tags:
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

                note_type_enum = None
                if note_type:
                    try:
                        note_type_enum = NoteType(note_type.lower())
                    except ValueError:
                        return f"Invalid note type: {note_type}. Valid types are: {', '.join(t.value for t in NoteType)}"

                results = self.search_service.search_combined(
                    text=query,
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
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_get_linked_notes")
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
                linked_notes = self.zettel_service.get_linked_notes(str(note_id), direction)
                if not linked_notes:
                    return f"No {direction} links found for note {note_id}."
                output = f"Found {len(linked_notes)} {direction} linked notes for {note_id}:\n\n"
                for i, note in enumerate(linked_notes, 1):
                    output += f"{i}. {note.title} (ID: {note.id})\n"
                    if note.tags:
                        output += f"   Tags: {', '.join(tag.name for tag in note.tags)}\n"
                    if direction in ["outgoing", "both"]:
                        source_note = self.zettel_service.get_note(str(note_id))
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
                return self.format_error_response(e)
        self.zk_get_linked_notes = zk_get_linked_notes

        @self.mcp.tool(name="zk_get_all_tags")
        def zk_get_all_tags() -> str:
            """Get all tags in the Zettelkasten.

            Returns alphabetically sorted list of all tags.
            Use this to find existing tags before creating new notes
            to maintain tag consistency across your knowledge base.
            """
            try:
                tags = self.zettel_service.get_all_tags()
                if not tags:
                    return "No tags found in the Zettelkasten."

                output = f"Found {len(tags)} tags:\n\n"
                tags.sort(key=lambda t: t.name.lower())
                for i, tag in enumerate(tags, 1):
                    output += f"{i}. {tag.name}\n"
                return output
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_find_similar_notes")
        def zk_find_similar_notes(
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
                similar_notes = self.zettel_service.find_similar_notes(str(note_id), threshold)
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
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_find_central_notes")
        def zk_find_central_notes(limit: int = 10) -> str:
            """Find the most connected notes in the Zettelkasten.

            Central notes have the most incoming and outgoing links, making them
            key hubs in your knowledge network. Good candidates for hub notes.

            Args:
                limit: Maximum results (default: 10)
            """
            try:
                central_notes = self.search_service.find_central_notes(limit)
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
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_find_orphaned_notes")
        def zk_find_orphaned_notes() -> str:
            """Find notes with no connections to other notes.

            Orphaned notes represent unintegrated knowledge. Review these periodically
            to either link them to existing notes or identify candidates for deletion.
            """
            try:
                orphans = self.search_service.find_orphaned_notes()
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
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_list_notes_by_date")
        def zk_list_notes_by_date(
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

                notes = self.search_service.find_notes_by_date_range(
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
                logger.error(f"Date parsing error: {str(e)}")
                return f"Error parsing date: {str(e)}"
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_rebuild_index")
        def zk_rebuild_index() -> str:
            """Rebuild the database index from markdown files.

            Use this if notes were edited outside the MCP server or if the
            database seems out of sync with the filesystem.
            """
            try:
                note_count_before = len(self.zettel_service.get_all_notes())
                self.zettel_service.rebuild_index()
                note_count_after = len(self.zettel_service.get_all_notes())
                return (
                    f"Database index rebuilt successfully.\n"
                    f"Notes processed: {note_count_after}\n"
                    f"Change in note count: {note_count_after - note_count_before}"
                )
            except Exception as e:
                logger.error(f"Failed to rebuild index: {e}", exc_info=True)
                return self.format_error_response(e)

    def _register_resources(self) -> None:

        @self.mcp.resource("zettelkasten://maintenance-status")
        def get_maintenance_status() -> dict:
            """Current Zettelkasten maintenance status.

            Returns pending cluster information for proactive maintenance prompts.
            Check this at session start to surface housekeeping opportunities.
            """
            report = self.cluster_service.load_report()

            if not report or not report.clusters:
                return {
                    "pending_maintenance": False,
                    "message": "No pending maintenance. Your Zettelkasten is well-organized!"
                }

            active_clusters = [
                c for c in report.clusters
                if c.id not in report.dismissed_cluster_ids
            ]

            if not active_clusters:
                return {
                    "pending_maintenance": False,
                    "message": "All detected clusters have been addressed or dismissed."
                }

            top = active_clusters[0]
            return {
                "pending_maintenance": True,
                "cluster_count": len(active_clusters),
                "top_cluster": {
                    "id": top.id,
                    "title": top.suggested_title,
                    "note_count": top.note_count,
                    "orphan_count": top.orphan_count,
                    "tags": top.tags[:5],
                    "score": top.score
                },
                "report_generated_at": report.generated_at.isoformat(),
                "report_age_hours": round(
                    (datetime.now() - report.generated_at).total_seconds() / 3600, 1
                )
            }

        @self.mcp.tool(name="zk_get_cluster_report")
        def zk_get_cluster_report(
            min_score: float = 0.5,
            limit: int = 5,
            include_notes: bool = False,
            refresh: bool = False
        ) -> str:
            """Get pending cluster analysis for structure note creation.

            Clusters are groups of notes sharing tags but lacking a structure note.
            High-scoring clusters are good candidates for new structure notes.

            Uses cached analysis by default. Set refresh=true to regenerate.
            Cluster analysis runs automatically via cron if configured.

            Scoring factors:
            - Note count (7-15 is ideal, >15 is overdue)
            - Orphan ratio (more orphans = more urgent)
            - Internal link density (fewer links = needs structure)
            - Recency (recent activity = active domain)

            Args:
                min_score: Minimum cluster score 0.0-1.0 (default: 0.5)
                limit: Maximum clusters to return (default: 5)
                include_notes: Include full note list per cluster (default: false)
                refresh: Force regeneration of cluster analysis (default: false)
            """
            try:
                if refresh:
                    report = self.cluster_service.detect_clusters()
                    self.cluster_service.save_report(report)
                else:
                    report = self.cluster_service.load_report()
                    if not report:
                        report = self.cluster_service.detect_clusters()
                        self.cluster_service.save_report(report)
                
                clusters = [c for c in report.clusters if c.score >= min_score][:limit]

                if not clusters:
                    return f"No clusters found with score >= {min_score}. Try lowering min_score or running with refresh=True."

                output = f"Cluster Analysis (generated {report.generated_at.strftime('%Y-%m-%d %H:%M')})\n"
                output += f"Stats: {report.stats['total_notes']} notes, {report.stats['total_orphans']} orphans, "
                output += f"{report.stats['clusters_needing_structure']} clusters need structure notes\n\n"
                
                for i, cluster in enumerate(clusters, 1):
                    output += f"{i}. {cluster.suggested_title}\n"
                    output += f"   ID: {cluster.id}\n"
                    output += f"   Score: {cluster.score} | Notes: {cluster.note_count} | Orphans: {cluster.orphan_count}\n"
                    output += f"   Tags: {', '.join(cluster.tags)}\n"
                    
                    if include_notes:
                        output += "   Notes:\n"
                        for note in cluster.notes[:10]:
                            output += f"     - {note['title']} ({note['id']})\n"
                        if len(cluster.notes) > 10:
                            output += f"     ... and {len(cluster.notes) - 10} more\n"
                    output += "\n"
                
                return output
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_create_structure_from_cluster")
        def zk_create_structure_from_cluster(
            cluster_id: str,
            title: Optional[str] = None,
            create_links: bool = True
        ) -> str:
            """Create a structure note from a detected cluster.

            Generates a structure note organizing all notes in the cluster,
            with bidirectional links to each member note.

            Run zk_get_cluster_report first to see available clusters and their IDs.

            Args:
                cluster_id: ID from cluster report (e.g. "jackson-mac-low-chance-operations")
                title: Override the suggested title (optional)
                create_links: Create bidirectional links to member notes (default: true)
            """
            try:
                report = self.cluster_service.load_report()
                if not report:
                    return "No cluster report found. Run zk_get_cluster_report(refresh=True) first."

                cluster = next((c for c in report.clusters if c.id == cluster_id), None)
                if not cluster:
                    available = ', '.join(c.id for c in report.clusters[:5])
                    return f"Cluster '{cluster_id}' not found. Available: {available}"

                final_title = title or cluster.suggested_title
                content = f"Structure note for {len(cluster.notes)} related notes.\n\n"
                content += f"## Overview\n\nThis cluster emerged from notes sharing these tags: {', '.join(cluster.tags)}.\n\n"
                content += "## Member Notes\n\n"
                
                for note_info in cluster.notes:
                    content += f"- [[{note_info['id']}]] {note_info['title']}\n"
                
                content += "\n## Synthesis\n\n_TODO: Synthesize key insights from these notes._\n"
                
                structure_note = self.zettel_service.create_note(
                    title=final_title,
                    content=content,
                    note_type=NoteType.STRUCTURE,
                    tags=cluster.tags[:5]
                )
                
                links_created = 0
                if create_links:
                    for note_info in cluster.notes:
                        try:
                            self.zettel_service.create_link(
                                source_id=structure_note.id,
                                target_id=note_info['id'],
                                link_type=LinkType.REFERENCE,
                                description="Member of structure note",
                                bidirectional=True
                            )
                            links_created += 1
                        except Exception as link_error:
                            logger.warning(f"Failed to create link to {note_info['id']}: {link_error}")
                
                self.cluster_service.dismiss_cluster(cluster_id)

                return f"Structure note created: {final_title} (ID: {structure_note.id})\nLinked to {links_created}/{len(cluster.notes)} member notes."
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_refresh_clusters")
        def zk_refresh_clusters() -> str:
            """Regenerate cluster analysis and save report.

            Analyzes all notes for emergent clusters based on:
            - Tag co-occurrence (tags that frequently appear together)
            - Connection patterns (notes that link to each other)
            - Structure note coverage (which clusters already have structure notes)

            Results saved to ~/.local/share/mcp/zettelkasten/cluster-analysis.json
            """
            try:
                report = self.cluster_service.detect_clusters()
                path = self.cluster_service.save_report(report)
                
                output = f"Cluster analysis complete.\n"
                output += f"Report saved to: {path}\n\n"
                output += f"Stats:\n"
                output += f"  Total notes: {report.stats['total_notes']}\n"
                output += f"  Orphaned notes: {report.stats['total_orphans']}\n"
                output += f"  Clusters detected: {report.stats['clusters_detected']}\n"
                output += f"  Clusters needing structure: {report.stats['clusters_needing_structure']}\n"
                
                if report.clusters:
                    output += f"\nTop clusters:\n"
                    for cluster in report.clusters[:3]:
                        output += f"  - {cluster.suggested_title} (score: {cluster.score})\n"
                
                return output
            except Exception as e:
                return self.format_error_response(e)

        @self.mcp.tool(name="zk_dismiss_cluster")
        def zk_dismiss_cluster(cluster_id: str) -> str:
            """Permanently dismiss a cluster from maintenance suggestions.

            Use this when a cluster has been reviewed and determined not to need
            a structure note, or when the user doesn't want to be reminded about it.

            Args:
                cluster_id: The cluster ID to dismiss (e.g. "poetry-craft-revision")
            """
            try:
                report = self.cluster_service.load_report()
                if not report:
                    return "No cluster report found. Run zk_refresh_clusters first."

                if cluster_id not in [c.id for c in report.clusters]:
                    available = ', '.join(c.id for c in report.clusters[:5])
                    return f"Cluster '{cluster_id}' not found. Available clusters: {available}"

                self.cluster_service.dismiss_cluster(cluster_id)
                return f"Cluster '{cluster_id}' dismissed. You won't be reminded about it again."
            except Exception as e:
                return self.format_error_response(e)

    def _register_prompts(self) -> None:
        """Register MCP prompts for knowledge workflows."""

        @self.mcp.prompt()
        def cluster_maintenance() -> str:
            """Check for pending cluster maintenance and offer to help.

            Call this at the start of a session to proactively surface
            Zettelkasten housekeeping opportunities.
            """
            report = self.cluster_service.load_report()

            if not report or not report.clusters:
                return "No pending cluster maintenance. Your Zettelkasten is well-organized!"

            active_clusters = [
                c for c in report.clusters
                if c.id not in report.dismissed_cluster_ids
            ]

            if not active_clusters:
                return "All detected clusters have been addressed or dismissed."

            cluster_summaries = []
            for c in active_clusters[:3]:
                cluster_summaries.append(
                    f"- **{c.suggested_title}** ({c.note_count} notes, {c.orphan_count} orphans, score: {c.score})\n"
                    f"  Tags: {', '.join(c.tags[:4])}\n"
                    f"  ID: `{c.id}`"
                )

            return f"""I found {len(active_clusters)} knowledge cluster(s) that might benefit from structure notes.

Top candidates:
{chr(10).join(cluster_summaries)}

Would you like me to:
1. **Create a structure note** for one of these clusters? (Just name it)
2. **Show more details** about a specific cluster?
3. **Skip for now** - I'll ask again next session
4. **Dismiss permanently** - Don't ask about these specific clusters again

Just let me know which cluster interests you, or say "skip" to move on."""

        @self.mcp.prompt()
        def knowledge_creation(content: str) -> str:
            """Process new information into atomic Zettelkasten notes.

            Use this workflow when you have text, articles, or ideas to add to your
            knowledge base. The workflow searches for existing related notes, extracts
            atomic ideas, creates properly linked notes, and updates structure notes.

            Args:
                content: The information to process (article text, notes, ideas, etc.)
            """
            return f"""I've attached information I'd like to incorporate into my Zettelkasten. Please:

First, search for existing notes that might be related before creating anything new.

Then, identify 3-5 key atomic ideas from this information and for each one:
1. Create a note with an appropriate title, type, and tags
2. Draft content in my own words with proper attribution
3. Find and create meaningful connections to existing notes
4. Update any relevant structure notes

After processing all ideas, provide a summary of the notes created, connections established, and any follow-up questions you have.

---

{content}"""

        @self.mcp.prompt()
        def knowledge_creation_batch(content: str) -> str:
            """Process larger volumes of information into the Zettelkasten.

            Use this workflow for processing books, long articles, or collections of
            related material. Extracts 5-10 atomic ideas, organizes them into clusters,
            and ensures quality and consistency with existing notes.

            Args:
                content: The larger text or collection to process
            """
            return f"""I've attached a larger text/collection of information to process into my Zettelkasten. Please:

1. First identify main themes and check my existing system for related notes and tags

2. Extract 5-10 distinct atomic ideas from this material, organized into logical clusters
   - Eliminate any concepts that duplicate my existing notes
   - Process each validated concept into a note with appropriate type, title, tags, and content
   - Create connections between related notes in this batch
   - Connect each new note to relevant existing notes in my system

3. Update or create structure notes as needed to integrate this batch of knowledge

4. Verify quality for each note:
   - Each note contains a single focused concept
   - All sources are properly cited
   - Each note has meaningful connections
   - Terminology is consistent with my existing system

Provide a summary of all notes created, connections established, and structure notes updated, along with any areas you've identified for follow-up work.

---

{content}"""

        @self.mcp.prompt()
        def knowledge_exploration(topic: str) -> str:
            """Explore how a topic connects to existing knowledge.

            Use this workflow to discover connections, find knowledge hubs, identify
            gaps, and map how new information relates to your existing Zettelkasten.

            Args:
                topic: The topic or concept to explore
            """
            return f"""I'd like to explore how this information connects to my existing Zettelkasten. Please:

1. Identify the central concepts in this information and find related notes in my system

2. Examine knowledge hubs in my Zettelkasten by:
   - Finding central notes related to these concepts
   - Mapping their connections and similar notes
   - Identifying promising knowledge paths to follow

3. Look for any gaps, contradictions, or orphaned notes that relate to these concepts

4. Create a conceptual map showing:
   - How this information fits with my existing knowledge
   - Unexpected connections discovered
   - Potential areas for development

Finally, summarize what you've learned about my Zettelkasten through this exploration and highlight the most valuable insights found.

---

Topic/concept to explore: {topic}"""

        @self.mcp.prompt()
        def knowledge_synthesis(content: str) -> str:
            """Synthesize higher-order insights from connected knowledge.

            Use this workflow to find bridges between unconnected areas, resolve
            contradictions, extend chains of thought, and create new permanent notes
            capturing emergent insights.

            Args:
                content: Information or context that might spark synthesis opportunities
            """
            return f"""I've attached information that might help synthesize ideas in my Zettelkasten. Please:

1. Find opportunities for synthesis by identifying:
   - Potential bridges between currently unconnected areas in my system
   - Contradictions that this information might help resolve
   - Incomplete chains of thought that could now be extended

2. For the most promising synthesis opportunities (3-5 max):
   - Create new permanent notes capturing the higher-order insights
   - Connect these synthesis notes to the contributing notes with appropriate link types
   - Update or create structure notes as needed

3. Identify any relevant fleeting notes that should be converted to permanent notes in light of this synthesis

4. Based on this synthesis work, highlight:
   - New questions that have emerged
   - Knowledge gaps revealed
   - Potential applications of the new understanding

Provide a summary of the insights discovered, notes created, and connections established through this synthesis process.

---

{content}"""

    def run(self) -> None:
        """Run the MCP server."""
        self.mcp.run()
