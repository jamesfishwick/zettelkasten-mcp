"""Integration tests for the Zettelkasten MCP system."""
from pathlib import Path
import pytest
from slipbox_mcp.models.schema import LinkType, NoteType
from slipbox_mcp.server.mcp_server import ZettelkastenMcpServer

# Tag shared by all notes in the knowledge-graph test
KG_TAG = "integration-test"


@pytest.fixture
def server(zettel_service):
    """MCP server wired to the isolated test ZettelService."""
    s = ZettelkastenMcpServer()
    s.zettel_service = zettel_service
    return s


# ---------------------------------------------------------------------------
# Note lifecycle
# ---------------------------------------------------------------------------

class TestNoteLifecycle:
    """End-to-end: create → retrieve → verify file on disk."""

    TITLE = "Integration Test Note"
    CONTENT = "This is a test of the complete note creation flow."
    TAGS = ["integration", "test", "flow"]

    def test_created_note_is_retrievable_with_full_content(self, zettel_service):
        """A note created through the service is retrieved with title heading and all tags."""
        # Arrange / Act
        note = zettel_service.create_note(
            title=self.TITLE,
            content=self.CONTENT,
            note_type=NoteType.PERMANENT,
            tags=self.TAGS,
        )

        # Assert
        retrieved = zettel_service.get_note(note.id)
        assert retrieved is not None, f"Note {note.id} not found after creation"
        assert retrieved.title == self.TITLE
        EXPECTED_CONTENT = f"# {self.TITLE}\n\n{self.CONTENT}"
        assert retrieved.content.strip() == EXPECTED_CONTENT.strip(), (
            "Retrieved content should include auto-prepended title heading"
        )
        assert {t.name for t in retrieved.tags} == set(self.TAGS), (
            f"Expected tags {set(self.TAGS)}, got {{{', '.join(t.name for t in retrieved.tags)}}}"
        )

    def test_created_note_exists_as_markdown_file_on_disk(self, zettel_service, test_config):
        """create() writes a .md file whose content includes title and body text."""
        # Arrange / Act
        note = zettel_service.create_note(
            title=self.TITLE,
            content=self.CONTENT,
            note_type=NoteType.PERMANENT,
            tags=self.TAGS,
        )
        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        note_file = notes_dir / f"{note.id}.md"

        # Assert
        assert note_file.exists(), f"Note file not found on disk: {note_file}"
        file_content = note_file.read_text()
        assert self.TITLE in file_content
        assert self.CONTENT in file_content


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------

class TestKnowledgeGraph:
    """Build a small multi-note graph and verify link traversal and tag queries."""

    def _create_graph(self, zettel_service):
        """Create four notes with six semantic links. Returns a dict keyed by role."""
        hub = zettel_service.create_note(
            title="Knowledge Graph Hub", content="Central hub.",
            note_type=NoteType.HUB, tags=["knowledge-graph", "hub", KG_TAG],
        )
        c1 = zettel_service.create_note(
            title="Concept One", content="First concept.",
            note_type=NoteType.PERMANENT, tags=["knowledge-graph", "concept", KG_TAG],
        )
        c2 = zettel_service.create_note(
            title="Concept Two", content="Second concept.",
            note_type=NoteType.PERMANENT, tags=["knowledge-graph", "concept", KG_TAG],
        )
        critique = zettel_service.create_note(
            title="Critique of Concepts", content="Critical perspective.",
            note_type=NoteType.PERMANENT, tags=["knowledge-graph", "critique", KG_TAG],
        )
        # hub → c1, hub → c2, hub → critique (3 outgoing from hub)
        zettel_service.create_link(hub.id, c1.id, LinkType.REFERENCE, bidirectional=True)
        zettel_service.create_link(hub.id, c2.id, LinkType.EXTENDS, bidirectional=True)
        zettel_service.create_link(hub.id, critique.id, LinkType.SUPPORTS, bidirectional=True)
        # cross-links between concepts
        zettel_service.create_link(c2.id, c1.id, LinkType.REFINES, bidirectional=True)
        zettel_service.create_link(critique.id, c1.id, LinkType.QUESTIONS, bidirectional=True)
        zettel_service.create_link(critique.id, c2.id, LinkType.CONTRADICTS, bidirectional=True)
        return {"hub": hub, "c1": c1, "c2": c2, "critique": critique}

    def test_hub_has_exactly_three_outgoing_links(self, zettel_service):
        """Hub links to c1, c2, and critique — no more, no fewer."""
        nodes = self._create_graph(zettel_service)
        hub_links = zettel_service.get_linked_notes(nodes["hub"].id, "outgoing")
        assert {n.id for n in hub_links} == {nodes["c1"].id, nodes["c2"].id, nodes["critique"].id}, (
            "Hub should have exactly 3 outgoing links to c1, c2, and critique"
        )

    def test_all_four_notes_share_the_integration_tag(self, zettel_service):
        """All four created notes carry the shared KG_TAG."""
        self._create_graph(zettel_service)
        tagged = zettel_service.get_notes_by_tag(KG_TAG)
        assert len(tagged) == 4, f"Expected 4 notes with tag '{KG_TAG}', got {len(tagged)}"


# ---------------------------------------------------------------------------
# Rebuild index
# ---------------------------------------------------------------------------

class TestRebuildIndex:
    """rebuild_index() re-syncs the DB from disk after external file edits."""

    ORIGINAL_CONTENT = "This is the original content."
    EDITED_CONTENT = "This content was manually edited outside the system."

    def test_rebuild_index_picks_up_external_file_edit(self, zettel_service, test_config):
        """After editing the .md file directly and calling rebuild_index(), the change is visible."""
        # Arrange — create note through service
        note = zettel_service.create_note(
            title="Original Note",
            content=self.ORIGINAL_CONTENT,
            tags=["rebuild-test"],
        )
        notes_dir = test_config.get_absolute_path(test_config.notes_dir)
        note_file = notes_dir / f"{note.id}.md"
        assert note_file.exists(), f"Note file not found: {note_file}"

        # Act — simulate external editor
        note_file.write_text(note_file.read_text().replace(self.ORIGINAL_CONTENT, self.EDITED_CONTENT))
        zettel_service.rebuild_index()

        # Assert
        updated = zettel_service.get_note(note.id)
        assert self.EDITED_CONTENT in updated.content, (
            f"Rebuilt index should reflect manually edited content. Got: {updated.content!r}"
        )
