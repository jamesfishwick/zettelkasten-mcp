"""Tests for the MCP server implementation."""
import pytest
from unittest.mock import patch, MagicMock

from slipbox_mcp.server.mcp_server import ZettelkastenMcpServer
from slipbox_mcp.models.schema import LinkType, NoteType


# ---------------------------------------------------------------------------
# Shared mock-server infrastructure
# ---------------------------------------------------------------------------

class MockServerBase:
    """Shared setup/teardown for tests that need a fully-mocked MCP server.

    Patches FastMCP, ZettelService, SearchService, and ClusterService so that
    server construction is fast and side-effect-free.  Tool functions registered
    with the mock are captured in ``self.registered_tools`` for direct invocation.
    """

    def setup_method(self):
        self.registered_tools: dict = {}
        self.mock_mcp = MagicMock()

        def _tool_decorator(*args, **kwargs):
            def _wrapper(func):
                self.registered_tools[kwargs.get("name")] = func
                return func
            return _wrapper

        self.mock_mcp.tool = _tool_decorator

        self.mock_zettel_service = MagicMock()
        self.mock_search_service = MagicMock()
        self.mock_cluster_service = MagicMock()

        self._patchers = [
            patch("slipbox_mcp.server.mcp_server.FastMCP", return_value=self.mock_mcp),
            patch("slipbox_mcp.server.mcp_server.ZettelService", return_value=self.mock_zettel_service),
            patch("slipbox_mcp.server.mcp_server.SearchService", return_value=self.mock_search_service),
            patch("slipbox_mcp.server.mcp_server.ClusterService", return_value=self.mock_cluster_service),
        ]
        for p in self._patchers:
            p.start()

        self.server = ZettelkastenMcpServer()

    def teardown_method(self):
        for p in self._patchers:
            p.stop()

    def _tool(self, name: str):
        """Return a registered tool function by name, failing fast if absent."""
        assert name in self.registered_tools, (
            f"Tool '{name}' was not registered. Available: {list(self.registered_tools)}"
        )
        return self.registered_tools[name]


# ---------------------------------------------------------------------------
# Server initialisation
# ---------------------------------------------------------------------------

class TestServerInitialization(MockServerBase):
    """MCP server wires up and initializes all services on construction."""

    def test_both_services_are_initialized(self):
        assert self.mock_zettel_service.initialize.called, "ZettelService.initialize() should be called"
        assert self.mock_search_service.initialize.called, "SearchService.initialize() should be called"


# ---------------------------------------------------------------------------
# Tool: zk_create_note
# ---------------------------------------------------------------------------

class TestCreateNoteTool(MockServerBase):
    """zk_create_note — happy path and tag parsing."""

    NOTE_ID = "test123"

    def setup_method(self):
        super().setup_method()
        self.mock_note = MagicMock()
        self.mock_note.id = self.NOTE_ID
        self.mock_zettel_service.create_note.return_value = self.mock_note

    def test_create_note_returns_success_message_with_id(self):
        # Arrange / Act
        result = self._tool("zk_create_note")(
            title="Test Note",
            content="Test content",
            note_type="permanent",
            tags="tag1, tag2",
        )

        # Assert — output
        assert "successfully" in result, f"Expected 'successfully' in result: {result!r}"
        assert self.NOTE_ID in result, f"Expected note ID {self.NOTE_ID!r} in result: {result!r}"

    def test_create_note_passes_parsed_tags_and_type_to_service(self):
        """Comma-separated tag string is split and NoteType enum is resolved."""
        # Act
        self._tool("zk_create_note")(
            title="Test Note",
            content="Test content",
            note_type="permanent",
            tags="tag1, tag2",
        )

        # Assert — service call
        self.mock_zettel_service.create_note.assert_called_with(
            title="Test Note",
            content="Test content",
            note_type=NoteType.PERMANENT,
            tags=["tag1", "tag2"],
            references=[],
        )


# ---------------------------------------------------------------------------
# Tool: zk_get_note
# ---------------------------------------------------------------------------

class TestGetNoteTool(MockServerBase):
    """zk_get_note — retrieves and formats a note."""

    NOTE_ID = "test123"
    NOTE_TITLE = "Test Note"
    NOTE_CONTENT = "Test content"

    def setup_method(self):
        super().setup_method()
        mock_note = MagicMock()
        mock_note.id = self.NOTE_ID
        mock_note.title = self.NOTE_TITLE
        mock_note.content = self.NOTE_CONTENT
        mock_note.note_type = NoteType.PERMANENT
        mock_note.created_at.isoformat.return_value = "2023-01-01T12:00:00"
        mock_note.updated_at.isoformat.return_value = "2023-01-01T12:30:00"
        tag1, tag2 = MagicMock(), MagicMock()
        tag1.name, tag2.name = "tag1", "tag2"
        mock_note.tags = [tag1, tag2]
        mock_note.links = []
        self.mock_zettel_service.get_note.return_value = mock_note

    def test_get_note_output_contains_title_id_and_content(self):
        # Act
        result = self._tool("zk_get_note")(identifier=self.NOTE_ID)

        # Assert
        assert f"# {self.NOTE_TITLE}" in result, "Output should include markdown title heading"
        assert f"ID: {self.NOTE_ID}" in result, "Output should include note ID"
        assert self.NOTE_CONTENT in result, "Output should include note body content"

    def test_get_note_calls_service_with_identifier(self):
        self._tool("zk_get_note")(identifier=self.NOTE_ID)
        self.mock_zettel_service.get_note.assert_called_with(self.NOTE_ID)


# ---------------------------------------------------------------------------
# Tool: zk_create_link
# ---------------------------------------------------------------------------

class TestCreateLinkTool(MockServerBase):
    """zk_create_link — creates and confirms bidirectional links."""

    SOURCE_ID = "source123"
    TARGET_ID = "target456"

    def setup_method(self):
        super().setup_method()
        source, target = MagicMock(), MagicMock()
        source.id, target.id = self.SOURCE_ID, self.TARGET_ID
        self.mock_zettel_service.create_link.return_value = (source, target)

    def test_bidirectional_link_result_mentions_both_ids(self):
        # Act
        result = self._tool("zk_create_link")(
            source_id=self.SOURCE_ID,
            target_id=self.TARGET_ID,
            link_type="extends",
            description="Test link",
            bidirectional=True,
        )

        # Assert
        assert "Bidirectional link created" in result, f"Unexpected result: {result!r}"
        assert self.SOURCE_ID in result
        assert self.TARGET_ID in result

    def test_create_link_passes_correct_enum_to_service(self):
        self._tool("zk_create_link")(
            source_id=self.SOURCE_ID,
            target_id=self.TARGET_ID,
            link_type="extends",
            description="Test link",
            bidirectional=True,
        )
        self.mock_zettel_service.create_link.assert_called_with(
            source_id=self.SOURCE_ID,
            target_id=self.TARGET_ID,
            link_type=LinkType.EXTENDS,
            description="Test link",
            bidirectional=True,
        )


# ---------------------------------------------------------------------------
# Tool: zk_search_notes
# ---------------------------------------------------------------------------

class TestSearchNotesTool(MockServerBase):
    """zk_search_notes — returns formatted results from search_combined."""

    def setup_method(self):
        super().setup_method()
        # Build two mock notes
        note1 = MagicMock()
        note1.id, note1.title, note1.content = "note1", "Note 1", "Note 1 content"
        t1a, t1b = MagicMock(), MagicMock()
        t1a.name, t1b.name = "tag1", "tag2"
        note1.tags = [t1a, t1b]
        note1.created_at.strftime.return_value = "2023-01-01"

        note2 = MagicMock()
        note2.id, note2.title, note2.content = "note2", "Note 2", "Note 2 content"
        t2 = MagicMock()
        t2.name = "tag1"
        note2.tags = [t2]
        note2.created_at.strftime.return_value = "2023-01-02"

        result1, result2 = MagicMock(), MagicMock()
        result1.note, result2.note = note1, note2
        self.mock_search_service.search_combined.return_value = [result1, result2]

    def test_search_result_count_and_note_titles_in_output(self):
        # Act
        result = self._tool("zk_search_notes")(
            query="test query",
            tags="tag1, tag2",
            note_type="permanent",
            limit=10,
        )

        # Assert
        assert "Found 2 matching notes" in result, f"Unexpected result header: {result!r}"
        assert "Note 1" in result
        assert "Note 2" in result

    def test_search_notes_calls_service_with_parsed_args(self):
        self._tool("zk_search_notes")(
            query="test query",
            tags="tag1, tag2",
            note_type="permanent",
            limit=10,
        )
        self.mock_search_service.search_combined.assert_called_with(
            query_text="test query",
            tags=["tag1", "tag2"],
            note_type=NoteType.PERMANENT,
        )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling(MockServerBase):
    """format_error_response() wraps all exception types uniformly."""

    def test_value_error_is_formatted(self):
        result = self.server.format_error_response(ValueError("Invalid input"))
        assert "Error: Invalid input" in result

    def test_io_error_is_formatted(self):
        result = self.server.format_error_response(IOError("File not found"))
        assert "Error: File not found" in result

    def test_generic_exception_is_formatted(self):
        result = self.server.format_error_response(Exception("Something went wrong"))
        assert "Error: Something went wrong" in result


# ---------------------------------------------------------------------------
# Model-level reference tests  (no server needed)
# ---------------------------------------------------------------------------

def test_note_has_references_field_defaulting_to_empty_list():
    from slipbox_mcp.models.schema import Note
    note = Note(title="Test", content="Body")
    assert hasattr(note, "references"), "Note model must have a 'references' field"
    assert note.references == []


def test_note_references_roundtrip_preserves_all_entries():
    from slipbox_mcp.models.schema import Note
    REFS = ["Ahrens, S. (2017). How to Take Smart Notes.", "https://zettelkasten.de"]
    note = Note(title="Test", content="Body", references=REFS)
    assert len(note.references) == 2, f"Expected 2 references, got {len(note.references)}"
    assert "Ahrens" in note.references[0]


def test_note_to_markdown_includes_references_in_frontmatter(note_repository):
    import frontmatter as fm
    from slipbox_mcp.models.schema import Note
    from slipbox_mcp.config import config

    REFS = ["Ahrens, S. (2017). How to Take Smart Notes.", "https://zettelkasten.de"]

    # Arrange / Act
    created = note_repository.create(Note(title="Cited Note", content="Body.", references=REFS))
    notes_dir = config.get_absolute_path(config.notes_dir)
    post = fm.load(str(notes_dir / f"{created.id}.md"))

    # Assert
    assert "references" in post.metadata, "references must appear in YAML frontmatter"
    assert len(post.metadata["references"]) == 2
    assert "Ahrens" in post.metadata["references"][0]


def test_references_roundtrip_via_file_read(note_repository):
    """References written to disk are parsed back correctly by get()."""
    from slipbox_mcp.models.schema import Note
    REF = "Luhmann, N. (1992). Communicating with Slip Boxes."

    created = note_repository.create(Note(title="Roundtrip Note", content="Body.", references=[REF]))
    retrieved = note_repository.get(created.id)

    assert retrieved.references == [REF], (
        f"Expected [{REF!r}] after file round-trip, got {retrieved.references!r}"
    )


def test_service_create_note_preserves_references(zettel_service):
    REF = "Ahrens, S. (2017). How to Take Smart Notes."
    note = zettel_service.create_note(title="Service Note", content="Body.", references=[REF])
    assert note.references == [REF]


def test_service_update_note_replaces_references(zettel_service):
    note = zettel_service.create_note(title="Note", content="Body.")
    updated = zettel_service.update_note(note.id, references=["New ref."])
    assert updated.references == ["New ref."]


def test_service_get_note_returns_references(zettel_service):
    REF = "Ahrens, S. (2017). How to Take Smart Notes."
    note = zettel_service.create_note(title="Cited", content="Body.", references=[REF])
    retrieved = zettel_service.get_note(note.id)
    assert "Ahrens" in retrieved.references[0]


def test_service_update_with_empty_list_clears_references(zettel_service):
    note = zettel_service.create_note(title="Note", content="Body.", references=["Some ref."])
    updated = zettel_service.update_note(note.id, references=[])
    assert updated.references == [], f"Expected empty references after clearing, got {updated.references!r}"


# ---------------------------------------------------------------------------
# Guard clauses — input validation
# ---------------------------------------------------------------------------

class TestGuardClauses(MockServerBase):
    """MCP tools reject invalid numeric parameters before calling services."""

    # Threshold bounds for zk_find_similar_notes
    VALID_THRESHOLD = 0.5
    THRESHOLD_ERROR = "Error: threshold must be between 0.0 and 1.0."
    LIMIT_ERROR = "Error: limit must be a positive integer."
    MIN_SCORE_ERROR = "Error: min_score must be between 0.0 and 1.0."

    def test_find_similar_notes_rejects_threshold_above_one(self):
        result = self._tool("zk_find_similar_notes")(note_id="abc", threshold=1.5)
        assert result == self.THRESHOLD_ERROR
        self.mock_zettel_service.find_similar_notes.assert_not_called()

    def test_find_similar_notes_rejects_negative_threshold(self):
        result = self._tool("zk_find_similar_notes")(note_id="abc", threshold=-0.1)
        assert result == self.THRESHOLD_ERROR

    def test_find_similar_notes_accepts_boundary_thresholds(self):
        """Threshold values 0.0 and 1.0 (inclusive) must pass the guard."""
        self.mock_zettel_service.find_similar_notes.return_value = []
        self._tool("zk_find_similar_notes")(note_id="abc", threshold=0.0)
        self._tool("zk_find_similar_notes")(note_id="abc", threshold=1.0)
        assert self.mock_zettel_service.find_similar_notes.call_count == 2, (
            "Both boundary calls should reach find_similar_notes"
        )

    def test_find_similar_notes_rejects_limit_zero(self):
        result = self._tool("zk_find_similar_notes")(note_id="abc", threshold=self.VALID_THRESHOLD, limit=0)
        assert result == self.LIMIT_ERROR
        self.mock_zettel_service.find_similar_notes.assert_not_called()

    def test_find_similar_notes_rejects_negative_limit(self):
        result = self._tool("zk_find_similar_notes")(note_id="abc", threshold=self.VALID_THRESHOLD, limit=-1)
        assert result == self.LIMIT_ERROR

    def test_find_central_notes_rejects_limit_zero(self):
        result = self._tool("zk_find_central_notes")(limit=0)
        assert result == self.LIMIT_ERROR
        self.mock_search_service.find_central_notes.assert_not_called()

    def test_find_central_notes_rejects_negative_limit(self):
        result = self._tool("zk_find_central_notes")(limit=-5)
        assert result == self.LIMIT_ERROR

    def test_get_cluster_report_rejects_min_score_above_one(self):
        result = self._tool("zk_get_cluster_report")(min_score=1.5)
        assert result == self.MIN_SCORE_ERROR

    def test_get_cluster_report_rejects_negative_min_score(self):
        result = self._tool("zk_get_cluster_report")(min_score=-0.1)
        assert result == self.MIN_SCORE_ERROR

    def test_get_cluster_report_accepts_boundary_min_scores(self):
        """min_score values 0.0 and 1.0 must pass the guard and reach load_report."""
        self.mock_cluster_service.load_report.return_value = None
        calls_before = self.mock_cluster_service.load_report.call_count
        result_low = self._tool("zk_get_cluster_report")(min_score=0.0)
        result_high = self._tool("zk_get_cluster_report")(min_score=1.0)
        assert result_low != self.MIN_SCORE_ERROR
        assert result_high != self.MIN_SCORE_ERROR
        # Guard must not fire for boundary values; load_report called exactly once per call
        assert self.mock_cluster_service.load_report.call_count == calls_before + 2, (
            "Both boundary calls should reach load_report (one call each)"
        )

    def test_get_cluster_report_rejects_limit_zero(self):
        result = self._tool("zk_get_cluster_report")(min_score=self.VALID_THRESHOLD, limit=0)
        assert result == self.LIMIT_ERROR
