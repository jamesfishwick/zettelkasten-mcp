"""MCP prompt registrations for knowledge workflows."""

from slipbox_mcp.server.descriptions import (
    PROMPT_CLUSTER_MAINTENANCE,
    PROMPT_CLUSTER_MAINTENANCE_ALL_DISMISSED,
    PROMPT_CLUSTER_MAINTENANCE_EMPTY,
    PROMPT_KNOWLEDGE_CREATION,
    PROMPT_KNOWLEDGE_CREATION_BATCH,
    PROMPT_KNOWLEDGE_EXPLORATION,
    PROMPT_KNOWLEDGE_SYNTHESIS,
)


def register_prompts(server) -> None:
    """Register all MCP prompts on the given server."""
    mcp = server.mcp
    cluster_service = server.cluster_service

    @mcp.prompt()
    def cluster_maintenance() -> str:
        """Check for pending cluster maintenance and offer to help.

        Call this at the start of a session to proactively surface
        Zettelkasten housekeeping opportunities.
        """
        report = cluster_service.load_report()

        if not report or not report.clusters:
            return PROMPT_CLUSTER_MAINTENANCE_EMPTY

        active_clusters = [
            c for c in report.clusters
            if c.id not in report.dismissed_cluster_ids
        ]

        if not active_clusters:
            return PROMPT_CLUSTER_MAINTENANCE_ALL_DISMISSED

        cluster_summaries = []
        for c in active_clusters[:3]:
            cluster_summaries.append(
                f"- **{c.suggested_title}** ({c.note_count} notes, {c.orphan_count} orphans, score: {c.score})\n"
                f"  Tags: {', '.join(c.tags[:4])}\n"
                f"  ID: `{c.id}`"
            )

        return PROMPT_CLUSTER_MAINTENANCE.format(
            active_count=len(active_clusters),
            cluster_summaries=chr(10).join(cluster_summaries),
        )

    @mcp.prompt()
    def knowledge_creation(content: str) -> str:
        """Process new information into atomic Zettelkasten notes.

        Use this workflow when you have text, articles, or ideas to add to your
        knowledge base. The workflow searches for existing related notes, extracts
        atomic ideas, creates properly linked notes, and updates structure notes.

        Args:
            content: The information to process (article text, notes, ideas, etc.)
        """
        return PROMPT_KNOWLEDGE_CREATION.format(content=content)

    @mcp.prompt()
    def knowledge_creation_batch(content: str) -> str:
        """Process larger volumes of information into the Zettelkasten.

        Use this workflow for processing books, long articles, or collections of
        related material. Extracts 5-10 atomic ideas, organizes them into clusters,
        and ensures quality and consistency with existing notes.

        Args:
            content: The larger text or collection to process
        """
        return PROMPT_KNOWLEDGE_CREATION_BATCH.format(content=content)

    @mcp.prompt()
    def knowledge_exploration(topic: str) -> str:
        """Explore how a topic connects to existing knowledge.

        Use this workflow to discover connections, find knowledge hubs, identify
        gaps, and map how new information relates to your existing Zettelkasten.

        Args:
            topic: The topic or concept to explore
        """
        return PROMPT_KNOWLEDGE_EXPLORATION.format(topic=topic)

    @mcp.prompt()
    def knowledge_synthesis(content: str) -> str:
        """Synthesize higher-order insights from connected knowledge.

        Use this workflow to find bridges between unconnected areas, resolve
        contradictions, extend chains of thought, and create new permanent notes
        capturing emergent insights.

        Args:
            content: Information or context that might spark synthesis opportunities
        """
        return PROMPT_KNOWLEDGE_SYNTHESIS.format(content=content)
