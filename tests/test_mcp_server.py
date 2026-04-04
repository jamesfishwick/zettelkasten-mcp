"""Tests for the MCP server implementation."""
from datetime import datetime
from unittest.mock import patch, MagicMock

from slipbox_mcp.server.mcp_server import ZettelkastenMcpServer, _parse_refs
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

    def test_server_is_initialized(self):
        assert self.server is not None, "Server should be constructed"


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

    def test_create_note_invalid_type_returns_error_listing_valid_types(self):
        """An unrecognised note_type string is rejected before calling the service."""
        # Act
        result = self._tool("zk_create_note")(
            title="Test", content="Body", note_type="bogus"
        )

        # Assert
        assert "Invalid note type: bogus" in result, f"Expected type error, got {result!r}"
        assert "permanent" in result, "Error should list valid types"
        self.mock_zettel_service.create_note.assert_not_called()


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
        assert self.SOURCE_ID in result, f"Expected source ID {self.SOURCE_ID!r} in result, got {result!r}"
        assert self.TARGET_ID in result, f"Expected target ID {self.TARGET_ID!r} in result, got {result!r}"

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

    def test_duplicate_link_returns_already_exists_message(self):
        """UNIQUE constraint violation is caught and returns a user-friendly message."""
        # Arrange
        from sqlalchemy.exc import IntegrityError
        self.mock_zettel_service.create_link.side_effect = IntegrityError(
            "INSERT", {}, Exception("UNIQUE constraint failed: links.source_id")
        )

        # Act
        result = self._tool("zk_create_link")(
            source_id=self.SOURCE_ID,
            target_id=self.TARGET_ID,
            link_type="extends",
        )

        # Assert
        assert "already exists" in result, f"Expected duplicate message, got {result!r}"

    def test_invalid_link_type_returns_error(self):
        """An unrecognised link_type string is rejected."""
        # Act
        result = self._tool("zk_create_link")(
            source_id=self.SOURCE_ID,
            target_id=self.TARGET_ID,
            link_type="bogus",
        )

        # Assert
        assert "Invalid link type: bogus" in result, f"Expected type error, got {result!r}"


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
        assert "Note 1" in result, f"Expected 'Note 1' in result, got {result!r}"
        assert "Note 2" in result, f"Expected 'Note 2' in result, got {result!r}"

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
        assert "Error: Invalid input" in result, f"Expected 'Error: Invalid input' in result, got {result!r}"

    def test_io_error_is_formatted(self):
        result = self.server.format_error_response(IOError("File not found"))
        assert "Error: File not found" in result, f"Expected 'Error: File not found' in result, got {result!r}"

    def test_generic_exception_is_formatted(self):
        result = self.server.format_error_response(Exception("Something went wrong"))
        assert "Error: Something went wrong" in result, f"Expected 'Error: Something went wrong' in result, got {result!r}"


# ---------------------------------------------------------------------------
# Model-level reference tests  (no server needed)
# ---------------------------------------------------------------------------

def test_note_has_references_field_defaulting_to_empty_list():
    from slipbox_mcp.models.schema import Note
    note = Note(title="Test", content="Body")
    assert hasattr(note, "references"), "Note model must have a 'references' field"
    assert note.references == [], f"Expected empty references, got {note.references!r}"


def test_note_references_roundtrip_preserves_all_entries():
    from slipbox_mcp.models.schema import Note
    REFS = ["Ahrens, S. (2017). How to Take Smart Notes.", "https://zettelkasten.de"]
    note = Note(title="Test", content="Body", references=REFS)
    assert len(note.references) == 2, f"Expected 2 references, got {len(note.references)}"
    assert "Ahrens" in note.references[0], f"Expected 'Ahrens' in first reference, got {note.references[0]!r}"


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
    assert len(post.metadata["references"]) == 2, f"Expected 2 references, got {len(post.metadata['references'])}"
    assert "Ahrens" in post.metadata["references"][0], f"Expected 'Ahrens' in first reference, got {post.metadata['references'][0]!r}"


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
    assert note.references == [REF], f"Expected [{REF!r}], got {note.references!r}"


def test_service_update_note_replaces_references(zettel_service):
    note = zettel_service.create_note(title="Note", content="Body.")
    updated = zettel_service.update_note(note.id, references=["New ref."])
    assert updated.references == ["New ref."], f"Expected ['New ref.'], got {updated.references!r}"


def test_service_get_note_returns_references(zettel_service):
    REF = "Ahrens, S. (2017). How to Take Smart Notes."
    note = zettel_service.create_note(title="Cited", content="Body.", references=[REF])
    retrieved = zettel_service.get_note(note.id)
    assert "Ahrens" in retrieved.references[0], f"Expected 'Ahrens' in first reference, got {retrieved.references[0]!r}"


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
        assert result == self.THRESHOLD_ERROR, f"Expected {self.THRESHOLD_ERROR!r}, got {result!r}"
        self.mock_zettel_service.find_similar_notes.assert_not_called()

    def test_find_similar_notes_rejects_negative_threshold(self):
        result = self._tool("zk_find_similar_notes")(note_id="abc", threshold=-0.1)
        assert result == self.THRESHOLD_ERROR, f"Expected {self.THRESHOLD_ERROR!r}, got {result!r}"

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
        assert result == self.LIMIT_ERROR, f"Expected {self.LIMIT_ERROR!r}, got {result!r}"
        self.mock_zettel_service.find_similar_notes.assert_not_called()

    def test_find_similar_notes_rejects_negative_limit(self):
        result = self._tool("zk_find_similar_notes")(note_id="abc", threshold=self.VALID_THRESHOLD, limit=-1)
        assert result == self.LIMIT_ERROR, f"Expected {self.LIMIT_ERROR!r}, got {result!r}"

    def test_find_central_notes_rejects_limit_zero(self):
        result = self._tool("zk_find_central_notes")(limit=0)
        assert result == self.LIMIT_ERROR, f"Expected {self.LIMIT_ERROR!r}, got {result!r}"
        self.mock_search_service.find_central_notes.assert_not_called()

    def test_find_central_notes_rejects_negative_limit(self):
        result = self._tool("zk_find_central_notes")(limit=-5)
        assert result == self.LIMIT_ERROR, f"Expected {self.LIMIT_ERROR!r}, got {result!r}"

    def test_get_cluster_report_rejects_min_score_above_one(self):
        result = self._tool("zk_get_cluster_report")(min_score=1.5)
        assert result == self.MIN_SCORE_ERROR, f"Expected {self.MIN_SCORE_ERROR!r}, got {result!r}"

    def test_get_cluster_report_rejects_negative_min_score(self):
        result = self._tool("zk_get_cluster_report")(min_score=-0.1)
        assert result == self.MIN_SCORE_ERROR, f"Expected {self.MIN_SCORE_ERROR!r}, got {result!r}"

    def test_get_cluster_report_accepts_boundary_min_scores(self):
        """min_score values 0.0 and 1.0 must pass the guard and reach load_report."""
        self.mock_cluster_service.load_report.return_value = None
        calls_before = self.mock_cluster_service.load_report.call_count
        result_low = self._tool("zk_get_cluster_report")(min_score=0.0)
        result_high = self._tool("zk_get_cluster_report")(min_score=1.0)
        assert result_low != self.MIN_SCORE_ERROR, "min_score=0.0 should pass guard"
        assert result_high != self.MIN_SCORE_ERROR, "min_score=1.0 should pass guard"
        # Guard must not fire for boundary values; load_report called exactly once per call
        assert self.mock_cluster_service.load_report.call_count == calls_before + 2, (
            "Both boundary calls should reach load_report (one call each)"
        )

    def test_get_cluster_report_rejects_limit_zero(self):
        result = self._tool("zk_get_cluster_report")(min_score=self.VALID_THRESHOLD, limit=0)
        assert result == self.LIMIT_ERROR, f"Expected {self.LIMIT_ERROR!r}, got {result!r}"


# ---------------------------------------------------------------------------
# Module-level helper: _parse_refs
# ---------------------------------------------------------------------------

class TestParseRefs:
    """_parse_refs splits newline-separated references and strips whitespace."""

    def test_splits_newline_separated_refs(self):
        # Arrange
        RAW = "Ahrens, S. (2017).\nhttps://zettelkasten.de"

        # Act
        result = _parse_refs(RAW)

        # Assert
        assert result == ["Ahrens, S. (2017).", "https://zettelkasten.de"], (
            f"Expected two stripped refs, got {result!r}"
        )

    def test_strips_whitespace_from_each_ref(self):
        # Arrange
        RAW = "  ref one  \n  ref two  "

        # Act
        result = _parse_refs(RAW)

        # Assert
        assert result == ["ref one", "ref two"], (
            f"Expected stripped refs, got {result!r}"
        )

    def test_empty_string_returns_empty_list(self):
        assert _parse_refs("") == [], "Empty string should produce empty list"

    def test_none_returns_empty_list(self):
        assert _parse_refs(None) == [], "None should produce empty list"

    def test_trailing_newline_ignored(self):
        # Arrange
        RAW = "ref one\nref two\n"

        # Act
        result = _parse_refs(RAW)

        # Assert
        assert result == ["ref one", "ref two"], (
            f"Trailing newline should not produce empty entry, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Tool: zk_update_note
# ---------------------------------------------------------------------------

class TestUpdateNoteTool(MockServerBase):
    """zk_update_note -- happy path, not-found, and invalid type."""

    NOTE_ID = "update123"
    NOTE_TITLE = "Updated Title"

    def setup_method(self):
        super().setup_method()
        self.mock_note = MagicMock()
        self.mock_note.id = self.NOTE_ID
        self.mock_note.title = self.NOTE_TITLE

    def test_happy_path_returns_success_with_id(self):
        # Arrange
        self.mock_zettel_service.get_note.return_value = self.mock_note
        self.mock_zettel_service.update_note.return_value = self.mock_note

        # Act
        result = self._tool("zk_update_note")(
            note_id=self.NOTE_ID, title=self.NOTE_TITLE
        )

        # Assert
        assert "updated successfully" in result, f"Expected success message, got {result!r}"
        assert self.NOTE_ID in result, f"Expected note ID in result, got {result!r}"

    def test_not_found_returns_error(self):
        # Arrange
        self.mock_zettel_service.get_note.return_value = None

        # Act
        result = self._tool("zk_update_note")(note_id="missing", title="X")

        # Assert
        assert "Note not found: missing" in result, f"Expected not-found message, got {result!r}"

    def test_invalid_note_type_returns_error_with_valid_types(self):
        # Arrange
        self.mock_zettel_service.get_note.return_value = self.mock_note

        # Act
        result = self._tool("zk_update_note")(
            note_id=self.NOTE_ID, note_type="bogus"
        )

        # Assert
        assert "Invalid note type: bogus" in result, f"Expected invalid-type error, got {result!r}"
        assert "permanent" in result, "Error should list valid types"


# ---------------------------------------------------------------------------
# Tool: zk_delete_note
# ---------------------------------------------------------------------------

class TestDeleteNoteTool(MockServerBase):
    """zk_delete_note -- happy path and not-found."""

    NOTE_ID = "delete123"

    def test_happy_path_returns_success_with_id(self):
        # Arrange
        mock_note = MagicMock()
        mock_note.id = self.NOTE_ID
        self.mock_zettel_service.get_note.return_value = mock_note

        # Act
        result = self._tool("zk_delete_note")(note_id=self.NOTE_ID)

        # Assert
        assert "deleted successfully" in result, f"Expected success message, got {result!r}"
        assert self.NOTE_ID in result, f"Expected note ID in result, got {result!r}"

    def test_not_found_returns_error(self):
        # Arrange
        self.mock_zettel_service.get_note.return_value = None

        # Act
        result = self._tool("zk_delete_note")(note_id="missing")

        # Assert
        assert "Note not found: missing" in result, f"Expected not-found message, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_remove_link
# ---------------------------------------------------------------------------

class TestRemoveLinkTool(MockServerBase):
    """zk_remove_link -- directional and bidirectional removal."""

    SOURCE_ID = "src001"
    TARGET_ID = "tgt002"

    def setup_method(self):
        super().setup_method()
        source, target = MagicMock(), MagicMock()
        source.id, target.id = self.SOURCE_ID, self.TARGET_ID
        self.mock_zettel_service.remove_link.return_value = (source, target)

    def test_directional_returns_from_to_message(self):
        # Act
        result = self._tool("zk_remove_link")(
            source_id=self.SOURCE_ID,
            target_id=self.TARGET_ID,
            bidirectional=False,
        )

        # Assert
        assert f"Link removed from {self.SOURCE_ID} to {self.TARGET_ID}" in result, (
            f"Expected directional removal message, got {result!r}"
        )

    def test_bidirectional_returns_between_message(self):
        # Act
        result = self._tool("zk_remove_link")(
            source_id=self.SOURCE_ID,
            target_id=self.TARGET_ID,
            bidirectional=True,
        )

        # Assert
        assert f"Bidirectional link removed between {self.SOURCE_ID} and {self.TARGET_ID}" in result, (
            f"Expected bidirectional removal message, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Tool: zk_get_linked_notes
# ---------------------------------------------------------------------------

class TestGetLinkedNotesTool(MockServerBase):
    """zk_get_linked_notes -- happy path, no links, invalid direction."""

    NOTE_ID = "center001"

    def _make_linked_note(self, note_id, title):
        note = MagicMock()
        note.id = note_id
        note.title = title
        tag = MagicMock()
        tag.name = "testtag"
        note.tags = [tag]
        note.links = []
        return note

    def test_happy_path_returns_linked_notes_list(self):
        # Arrange
        linked = self._make_linked_note("linked1", "Linked Note 1")
        self.mock_zettel_service.get_linked_notes.return_value = [linked]
        source_note = MagicMock()
        source_note.links = []
        self.mock_zettel_service.get_note.return_value = source_note

        # Act
        result = self._tool("zk_get_linked_notes")(
            note_id=self.NOTE_ID, direction="outgoing"
        )

        # Assert
        assert "Linked Note 1" in result, f"Expected linked note title, got {result!r}"
        assert "linked1" in result, f"Expected linked note ID, got {result!r}"
        assert "1 outgoing linked notes" in result, f"Expected count header, got {result!r}"

    def test_no_links_returns_message(self):
        # Arrange
        self.mock_zettel_service.get_linked_notes.return_value = []

        # Act
        result = self._tool("zk_get_linked_notes")(
            note_id=self.NOTE_ID, direction="both"
        )

        # Assert
        assert "No both links found" in result, f"Expected no-links message, got {result!r}"

    def test_invalid_direction_returns_error(self):
        # Act
        result = self._tool("zk_get_linked_notes")(
            note_id=self.NOTE_ID, direction="sideways"
        )

        # Assert
        assert "Invalid direction: sideways" in result, (
            f"Expected invalid-direction error, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Tool: zk_get_all_tags
# ---------------------------------------------------------------------------

class TestGetAllTagsTool(MockServerBase):
    """zk_get_all_tags -- happy path and empty."""

    def test_happy_path_returns_sorted_tag_list(self):
        # Arrange
        tag_a, tag_b, tag_c = MagicMock(), MagicMock(), MagicMock()
        tag_a.name = "zebra"
        tag_b.name = "alpha"
        tag_c.name = "middle"
        self.mock_zettel_service.get_all_tags.return_value = [tag_a, tag_b, tag_c]

        # Act
        result = self._tool("zk_get_all_tags")()

        # Assert
        assert "Found 3 tags" in result, f"Expected tag count header, got {result!r}"
        alpha_pos = result.index("alpha")
        middle_pos = result.index("middle")
        zebra_pos = result.index("zebra")
        assert alpha_pos < middle_pos < zebra_pos, (
            f"Tags should be alphabetically sorted, got {result!r}"
        )

    def test_empty_returns_no_tags_message(self):
        # Arrange
        self.mock_zettel_service.get_all_tags.return_value = []

        # Act
        result = self._tool("zk_get_all_tags")()

        # Assert
        assert "No tags found" in result, f"Expected no-tags message, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_find_similar_notes
# ---------------------------------------------------------------------------

class TestFindSimilarNotesTool(MockServerBase):
    """zk_find_similar_notes -- happy path with results."""

    NOTE_ID = "sim001"
    SIMILAR_SCORE = 0.85

    def test_happy_path_returns_formatted_results_with_scores(self):
        # Arrange
        similar_note = MagicMock()
        similar_note.id = "sim002"
        similar_note.title = "Similar Note"
        similar_note.content = "Some content here"
        tag = MagicMock()
        tag.name = "shared-tag"
        similar_note.tags = [tag]
        self.mock_zettel_service.find_similar_notes.return_value = [
            (similar_note, self.SIMILAR_SCORE)
        ]

        # Act
        result = self._tool("zk_find_similar_notes")(
            note_id=self.NOTE_ID, threshold=0.3
        )

        # Assert
        assert "Similar Note" in result, f"Expected similar note title, got {result!r}"
        assert "0.85" in result, f"Expected similarity score, got {result!r}"
        assert "sim002" in result, f"Expected similar note ID, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_find_central_notes
# ---------------------------------------------------------------------------

class TestFindCentralNotesTool(MockServerBase):
    """zk_find_central_notes -- happy path with results."""

    CONNECTION_COUNT = 12

    def test_happy_path_returns_formatted_results_with_counts(self):
        # Arrange
        central_note = MagicMock()
        central_note.id = "hub001"
        central_note.title = "Central Hub"
        central_note.content = "Hub content"
        tag = MagicMock()
        tag.name = "hub-tag"
        central_note.tags = [tag]
        self.mock_search_service.find_central_notes.return_value = [
            (central_note, self.CONNECTION_COUNT)
        ]

        # Act
        result = self._tool("zk_find_central_notes")(limit=5)

        # Assert
        assert "Central Hub" in result, f"Expected central note title, got {result!r}"
        assert str(self.CONNECTION_COUNT) in result, (
            f"Expected connection count {self.CONNECTION_COUNT}, got {result!r}"
        )
        assert "hub001" in result, f"Expected note ID, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_find_orphaned_notes
# ---------------------------------------------------------------------------

class TestFindOrphanedNotesTool(MockServerBase):
    """zk_find_orphaned_notes -- happy path and empty."""

    def test_happy_path_returns_formatted_orphan_list(self):
        # Arrange
        orphan = MagicMock()
        orphan.id = "orphan001"
        orphan.title = "Lonely Note"
        orphan.content = "No friends"
        orphan.tags = []
        self.mock_search_service.find_orphaned_notes.return_value = [orphan]

        # Act
        result = self._tool("zk_find_orphaned_notes")()

        # Assert
        assert "Lonely Note" in result, f"Expected orphan title, got {result!r}"
        assert "orphan001" in result, f"Expected orphan ID, got {result!r}"
        assert "1 orphaned notes" in result, f"Expected count header, got {result!r}"

    def test_empty_returns_no_orphans_message(self):
        # Arrange
        self.mock_search_service.find_orphaned_notes.return_value = []

        # Act
        result = self._tool("zk_find_orphaned_notes")()

        # Assert
        assert result == "No orphaned notes found.", (
            f"Expected exact no-orphans message, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Tool: zk_list_notes_by_date
# ---------------------------------------------------------------------------

class TestListNotesByDateTool(MockServerBase):
    """zk_list_notes_by_date -- happy path, no results, and invalid date."""

    def _make_dated_note(self, note_id, title, date_str):
        note = MagicMock()
        note.id = note_id
        note.title = title
        note.content = "Some content"
        note.tags = []
        note.created_at.strftime.return_value = date_str
        note.updated_at.strftime.return_value = date_str
        return note

    def test_happy_path_returns_formatted_date_list(self):
        # Arrange
        note = self._make_dated_note("date001", "Dated Note", "2023-06-15 10:00")
        self.mock_search_service.find_notes_by_date_range.return_value = [note]

        # Act
        result = self._tool("zk_list_notes_by_date")(
            start_date="2023-06-01", end_date="2023-06-30", limit=10
        )

        # Assert
        assert "Dated Note" in result, f"Expected note title, got {result!r}"
        assert "date001" in result, f"Expected note ID, got {result!r}"
        assert "1 results" in result, f"Expected result count, got {result!r}"

    def test_no_results_returns_message(self):
        # Arrange
        self.mock_search_service.find_notes_by_date_range.return_value = []

        # Act
        result = self._tool("zk_list_notes_by_date")(
            start_date="2099-01-01", end_date="2099-12-31"
        )

        # Assert
        assert "No notes found" in result, f"Expected no-notes message, got {result!r}"

    def test_invalid_date_returns_parsing_error(self):
        # Act
        result = self._tool("zk_list_notes_by_date")(start_date="not-a-date")

        # Assert
        assert "Error parsing date" in result, f"Expected date parsing error, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_rebuild_index
# ---------------------------------------------------------------------------

class TestRebuildIndexTool(MockServerBase):
    """zk_rebuild_index -- happy path."""

    NOTE_COUNT = 42

    def test_happy_path_returns_success_with_counts(self):
        # Arrange
        self.mock_zettel_service.get_all_notes.return_value = [MagicMock()] * self.NOTE_COUNT

        # Act
        result = self._tool("zk_rebuild_index")()

        # Assert
        assert "rebuilt successfully" in result, f"Expected success message, got {result!r}"
        assert str(self.NOTE_COUNT) in result, (
            f"Expected note count {self.NOTE_COUNT} in result, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Tool: zk_get_cluster_report (happy path)
# ---------------------------------------------------------------------------

class TestGetClusterReportTool(MockServerBase):
    """zk_get_cluster_report -- happy path with results."""

    def _make_report_with_clusters(self):
        from slipbox_mcp.services.cluster_service import ClusterCandidate, ClusterReport
        cluster = ClusterCandidate(
            id="poetry-craft",
            suggested_title="Poetry & Craft",
            tags=["poetry", "craft"],
            notes=[{"id": "n1", "title": "Note 1"}, {"id": "n2", "title": "Note 2"}],
            note_count=2,
            orphan_count=1,
            internal_links=1,
            density=0.5,
            score=0.8,
        )
        report = ClusterReport(
            generated_at=datetime(2023, 6, 15, 10, 0),
            clusters=[cluster],
            stats={
                "total_notes": 10,
                "total_orphans": 3,
                "clusters_detected": 1,
                "clusters_needing_structure": 1,
            },
        )
        return report

    def test_happy_path_returns_formatted_clusters(self):
        # Arrange
        report = self._make_report_with_clusters()
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._tool("zk_get_cluster_report")(min_score=0.5)

        # Assert
        assert "Poetry & Craft" in result, f"Expected cluster title, got {result!r}"
        assert "poetry-craft" in result, f"Expected cluster ID, got {result!r}"
        assert "0.8" in result, f"Expected cluster score, got {result!r}"

    def test_no_clusters_above_min_score_returns_message(self):
        # Arrange
        report = self._make_report_with_clusters()
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._tool("zk_get_cluster_report")(min_score=0.99)

        # Assert
        assert "No clusters found" in result, f"Expected no-clusters message, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_refresh_clusters
# ---------------------------------------------------------------------------

class TestRefreshClustersTool(MockServerBase):
    """zk_refresh_clusters -- happy path."""

    def test_happy_path_returns_stats(self):
        from slipbox_mcp.services.cluster_service import ClusterCandidate, ClusterReport

        # Arrange
        cluster = ClusterCandidate(
            id="test-cluster",
            suggested_title="Test Cluster",
            tags=["test"],
            notes=[],
            note_count=5,
            orphan_count=2,
            internal_links=3,
            density=0.6,
            score=0.7,
        )
        report = ClusterReport(
            generated_at=datetime(2023, 6, 15, 10, 0),
            clusters=[cluster],
            stats={
                "total_notes": 20,
                "total_orphans": 5,
                "clusters_detected": 1,
                "clusters_needing_structure": 1,
            },
        )
        self.mock_cluster_service.detect_clusters.return_value = report
        self.mock_cluster_service.save_report.return_value = "/tmp/report.json"

        # Act
        result = self._tool("zk_refresh_clusters")()

        # Assert
        assert "Cluster analysis complete" in result, f"Expected success header, got {result!r}"
        assert "20" in result, f"Expected total notes count, got {result!r}"
        assert "Test Cluster" in result, f"Expected top cluster name, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_dismiss_cluster
# ---------------------------------------------------------------------------

class TestDismissClusterTool(MockServerBase):
    """zk_dismiss_cluster -- happy path and not-found."""

    def _make_report(self, cluster_ids):
        from slipbox_mcp.services.cluster_service import ClusterCandidate, ClusterReport
        clusters = []
        for cid in cluster_ids:
            clusters.append(ClusterCandidate(
                id=cid,
                suggested_title=f"Cluster {cid}",
                tags=["t"],
                notes=[],
                note_count=1,
                orphan_count=0,
                internal_links=0,
                density=0.0,
                score=0.5,
            ))
        return ClusterReport(
            generated_at=datetime(2023, 1, 1),
            clusters=clusters,
            stats={"total_notes": 1, "total_orphans": 0,
                   "clusters_detected": len(clusters),
                   "clusters_needing_structure": len(clusters)},
        )

    def test_happy_path_dismisses_cluster(self):
        # Arrange
        CLUSTER_ID = "poetry-craft"
        self.mock_cluster_service.load_report.return_value = self._make_report([CLUSTER_ID])

        # Act
        result = self._tool("zk_dismiss_cluster")(cluster_id=CLUSTER_ID)

        # Assert
        assert "dismissed" in result, f"Expected dismiss confirmation, got {result!r}"
        assert CLUSTER_ID in result, f"Expected cluster ID in result, got {result!r}"
        self.mock_cluster_service.dismiss_cluster.assert_called_once_with(CLUSTER_ID)

    def test_not_found_returns_error(self):
        # Arrange
        self.mock_cluster_service.load_report.return_value = self._make_report(["existing"])

        # Act
        result = self._tool("zk_dismiss_cluster")(cluster_id="nonexistent")

        # Assert
        assert "not found" in result, f"Expected not-found message, got {result!r}"

    def test_no_report_returns_error(self):
        # Arrange
        self.mock_cluster_service.load_report.return_value = None

        # Act
        result = self._tool("zk_dismiss_cluster")(cluster_id="any")

        # Assert
        assert "No cluster report found" in result, f"Expected no-report message, got {result!r}"


# ---------------------------------------------------------------------------
# Tool: zk_create_structure_from_cluster
# ---------------------------------------------------------------------------

class TestCreateStructureFromClusterTool(MockServerBase):
    """zk_create_structure_from_cluster -- happy path and not-found."""

    def _make_report(self, cluster_id, note_infos):
        from slipbox_mcp.services.cluster_service import ClusterCandidate, ClusterReport
        cluster = ClusterCandidate(
            id=cluster_id,
            suggested_title=f"Structure: {cluster_id}",
            tags=["tag1", "tag2"],
            notes=note_infos,
            note_count=len(note_infos),
            orphan_count=0,
            internal_links=0,
            density=0.0,
            score=0.8,
        )
        return ClusterReport(
            generated_at=datetime(2023, 6, 15),
            clusters=[cluster],
            stats={"total_notes": 10, "total_orphans": 2,
                   "clusters_detected": 1, "clusters_needing_structure": 1},
        )

    def test_happy_path_creates_structure_note_with_links(self):
        # Arrange
        CLUSTER_ID = "poetry-craft"
        NOTE_INFOS = [{"id": "n1", "title": "Note 1"}, {"id": "n2", "title": "Note 2"}]
        report = self._make_report(CLUSTER_ID, NOTE_INFOS)
        self.mock_cluster_service.load_report.return_value = report

        structure_note = MagicMock()
        structure_note.id = "struct001"
        self.mock_zettel_service.create_note.return_value = structure_note
        self.mock_zettel_service.create_link.return_value = (MagicMock(), MagicMock())

        # Act
        result = self._tool("zk_create_structure_from_cluster")(
            cluster_id=CLUSTER_ID
        )

        # Assert
        assert "Structure note created" in result, f"Expected creation message, got {result!r}"
        assert "struct001" in result, f"Expected structure note ID, got {result!r}"
        assert "2/2 member notes" in result, f"Expected link count, got {result!r}"
        self.mock_cluster_service.dismiss_cluster.assert_called_once_with(CLUSTER_ID)

    def test_cluster_not_found_returns_error(self):
        # Arrange
        report = self._make_report("existing", [])
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._tool("zk_create_structure_from_cluster")(
            cluster_id="nonexistent"
        )

        # Assert
        assert "not found" in result, f"Expected not-found message, got {result!r}"

    def test_no_report_returns_error(self):
        # Arrange
        self.mock_cluster_service.load_report.return_value = None

        # Act
        result = self._tool("zk_create_structure_from_cluster")(cluster_id="any")

        # Assert
        assert "No cluster report found" in result, f"Expected no-report message, got {result!r}"


# ---------------------------------------------------------------------------
# Extended mock base that also captures resource and prompt registrations
# ---------------------------------------------------------------------------

class MockServerWithPromptsBase(MockServerBase):
    """Extends MockServerBase to also capture resource and prompt registrations.

    Duplicates setup_method rather than calling super() because the resource/
    prompt decorator stubs must be installed on mock_mcp *before*
    ZettelkastenMcpServer() is constructed (which super() triggers).
    """

    def setup_method(self):
        self.registered_resources: dict = {}
        self.registered_prompts: dict = {}
        self.registered_tools: dict = {}
        self.mock_mcp = MagicMock()

        def _tool_decorator(*args, **kwargs):
            def _wrapper(func):
                self.registered_tools[kwargs.get("name")] = func
                return func
            return _wrapper

        def _resource_decorator(uri):
            def _wrapper(func):
                self.registered_resources[uri] = func
                return func
            return _wrapper

        def _prompt_decorator():
            def _wrapper(func):
                self.registered_prompts[func.__name__] = func
                return func
            return _wrapper

        self.mock_mcp.tool = _tool_decorator
        self.mock_mcp.resource = _resource_decorator
        self.mock_mcp.prompt = _prompt_decorator

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

    def _resource(self, uri: str):
        assert uri in self.registered_resources, (
            f"Resource '{uri}' not registered. Available: {list(self.registered_resources)}"
        )
        return self.registered_resources[uri]

    def _prompt(self, name: str):
        assert name in self.registered_prompts, (
            f"Prompt '{name}' not registered. Available: {list(self.registered_prompts)}"
        )
        return self.registered_prompts[name]


# ---------------------------------------------------------------------------
# Helpers for cluster-related tests
# ---------------------------------------------------------------------------

def _make_cluster_report(active=True, dismissed_ids=None):
    """Build a ClusterReport with one cluster for testing."""
    from slipbox_mcp.services.cluster_service import ClusterCandidate, ClusterReport

    cluster = ClusterCandidate(
        id="poetry-craft-revision",
        suggested_title="Poetry Knowledge Map",
        tags=["poetry", "craft", "revision"],
        notes=[{"id": "n1", "title": "Note 1"}],
        note_count=7,
        orphan_count=2,
        internal_links=3,
        density=0.15,
        score=0.72,
        newest_date=datetime(2026, 3, 30),
    )
    return ClusterReport(
        generated_at=datetime(2026, 4, 1, 12, 0),
        clusters=[cluster],
        stats={
            "total_notes": 50,
            "total_orphans": 10,
            "clusters_detected": 3,
            "clusters_needing_structure": 1,
        },
        dismissed_cluster_ids=dismissed_ids or [],
    )


# ---------------------------------------------------------------------------
# Resource: slipbox://maintenance-status
# ---------------------------------------------------------------------------

MAINTENANCE_URI = "slipbox://maintenance-status"


class TestMaintenanceStatusResourceNoReport(MockServerWithPromptsBase):
    """get_maintenance_status returns safe defaults when no report exists."""

    def test_no_report_returns_pending_false(self):
        # Arrange
        self.mock_cluster_service.load_report.return_value = None

        # Act
        result = self._resource(MAINTENANCE_URI)()

        # Assert
        assert result["pending_maintenance"] is False, (
            "pending_maintenance should be False when no report exists"
        )


class TestMaintenanceStatusResourceWithClusters(MockServerWithPromptsBase):
    """get_maintenance_status surfaces active clusters."""

    def test_active_clusters_returns_pending_true(self):
        # Arrange
        report = _make_cluster_report(active=True)
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._resource(MAINTENANCE_URI)()

        # Assert
        assert result["pending_maintenance"] is True, (
            "pending_maintenance should be True when active clusters exist"
        )

    def test_active_clusters_returns_correct_count(self):
        # Arrange
        report = _make_cluster_report(active=True)
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._resource(MAINTENANCE_URI)()

        # Assert
        EXPECTED_COUNT = 1
        assert result["cluster_count"] == EXPECTED_COUNT, (
            f"Expected cluster_count={EXPECTED_COUNT}, got {result['cluster_count']}"
        )

    def test_active_clusters_includes_top_cluster_details(self):
        # Arrange
        report = _make_cluster_report(active=True)
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._resource(MAINTENANCE_URI)()

        # Assert
        top = result["top_cluster"]
        assert top["id"] == "poetry-craft-revision", (
            f"Expected top cluster id 'poetry-craft-revision', got {top['id']!r}"
        )
        assert top["title"] == "Poetry Knowledge Map", (
            f"Unexpected top cluster title: {top['title']!r}"
        )
        assert top["note_count"] == 7, "Top cluster should have note_count=7"
        assert top["score"] == 0.72, "Top cluster should have score=0.72"


class TestMaintenanceStatusResourceAllDismissed(MockServerWithPromptsBase):
    """get_maintenance_status when all clusters are dismissed."""

    def test_all_dismissed_returns_pending_false(self):
        # Arrange
        report = _make_cluster_report(
            dismissed_ids=["poetry-craft-revision"]
        )
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._resource(MAINTENANCE_URI)()

        # Assert
        assert result["pending_maintenance"] is False, (
            "pending_maintenance should be False when all clusters are dismissed"
        )


# ---------------------------------------------------------------------------
# Prompt: cluster_maintenance
# ---------------------------------------------------------------------------

class TestClusterMaintenancePromptNoReport(MockServerWithPromptsBase):
    """cluster_maintenance prompt with no report."""

    def test_no_report_returns_no_pending_message(self):
        # Arrange
        self.mock_cluster_service.load_report.return_value = None

        # Act
        result = self._prompt("cluster_maintenance")()

        # Assert
        assert "No pending cluster maintenance" in result, (
            f"Expected 'No pending' message, got {result!r}"
        )


class TestClusterMaintenancePromptWithClusters(MockServerWithPromptsBase):
    """cluster_maintenance prompt with active clusters."""

    def test_active_clusters_includes_formatted_summaries(self):
        # Arrange
        report = _make_cluster_report(active=True)
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._prompt("cluster_maintenance")()

        # Assert
        assert "Poetry Knowledge Map" in result, (
            "Prompt output should include cluster title"
        )
        assert "7 notes" in result, "Prompt output should include note count"
        assert "2 orphans" in result, "Prompt output should include orphan count"


class TestClusterMaintenancePromptAllDismissed(MockServerWithPromptsBase):
    """cluster_maintenance prompt when all clusters are dismissed."""

    def test_all_dismissed_returns_addressed_message(self):
        # Arrange
        report = _make_cluster_report(
            dismissed_ids=["poetry-craft-revision"]
        )
        self.mock_cluster_service.load_report.return_value = report

        # Act
        result = self._prompt("cluster_maintenance")()

        # Assert
        assert "addressed or dismissed" in result, (
            f"Expected 'addressed or dismissed' message, got {result!r}"
        )


