"""Tests for SearchService."""
from slipbox_mcp.models.schema import LinkType, NoteType


# Convenience wrapper: creates a note through the service using keyword args.
# This keeps test arrange-sections readable without repeating boilerplate.
def _note(zettel_service, title, tags=None, note_type=NoteType.PERMANENT, content="Body."):
    return zettel_service.create_note(
        title=title,
        content=content,
        note_type=note_type,
        tags=tags or [],
    )


# ---------------------------------------------------------------------------
# Tag search
# ---------------------------------------------------------------------------

class TestSearchByTag:
    """search_by_tag() — single string and list variants."""

    def test_single_tag_returns_matching_notes(self, zettel_service, search_service):
        """search_by_tag(str) finds every note carrying that tag."""
        # Arrange
        note1 = _note(zettel_service, "Programming Basics", tags=["programming", "basics"])
        note2 = _note(zettel_service, "Python Basics", tags=["python", "programming", "basics"])
        _note(zettel_service, "Advanced JavaScript", tags=["javascript", "advanced"])

        # Act
        results = search_service.search_by_tag("programming")

        # Assert
        result_ids = {n.id for n in results}
        assert note1.id in result_ids, "Programming Basics should match tag 'programming'"
        assert note2.id in result_ids, "Python Basics should match tag 'programming'"

    def test_tag_list_returns_union_of_matches(self, zettel_service, search_service):
        """search_by_tag(list) returns notes matching any of the tags (OR semantics)."""
        # Arrange
        note_a = _note(zettel_service, "Alpha", tags=["alpha"])
        note_b = _note(zettel_service, "Beta", tags=["beta"])
        note_c = _note(zettel_service, "Gamma", tags=["gamma"])

        # Act
        results = search_service.search_by_tag(["alpha", "beta"])

        # Assert
        ids = {n.id for n in results}
        assert note_a.id in ids, "Alpha note should be in results (matched 'alpha')"
        assert note_b.id in ids, "Beta note should be in results (matched 'beta')"
        assert note_c.id not in ids, "Gamma note should not appear (unmatched tag)"

    def test_tag_list_does_not_return_duplicates(self, zettel_service, search_service):
        """A note tagged with two searched tags must not appear twice in results."""
        # Arrange
        note = _note(zettel_service, "Multi Tag", tags=["alpha", "beta"])

        # Act
        results = search_service.search_by_tag(["alpha", "beta"])

        # Assert
        appearances = [n.id for n in results].count(note.id)
        assert appearances == 1, f"Note appeared {appearances} times; expected exactly 1"

    def test_string_path_delegates_correctly(self, zettel_service, search_service):
        """search_by_tag(str) reaches the single-tag code path."""
        # Arrange
        note = _note(zettel_service, "Solo Tag", tags=["solo"])

        # Act
        results = search_service.search_by_tag("solo")

        # Assert
        assert any(n.id == note.id for n in results), "Solo-tagged note should appear in results"


# ---------------------------------------------------------------------------
# Link-based search
# ---------------------------------------------------------------------------

class TestSearchByLink:
    """get_linked_notes() — outgoing, incoming, and both directions."""

    def test_outgoing_links_returns_targets(self, zettel_service):
        """Outgoing search returns the two notes the source links to."""
        # Arrange
        source = _note(zettel_service, "Source")
        target1 = _note(zettel_service, "Target 1")
        target2 = _note(zettel_service, "Target 2")
        _note(zettel_service, "Unrelated")
        zettel_service.create_link(source.id, target1.id, LinkType.REFERENCE)
        zettel_service.create_link(source.id, target2.id, LinkType.EXTENDS)

        # Act
        results = zettel_service.get_linked_notes(source.id, "outgoing")

        # Assert
        result_ids = {n.id for n in results}
        assert result_ids == {target1.id, target2.id}, (
            f"Expected exactly {{target1, target2}}, got {result_ids}"
        )

    def test_incoming_links_returns_sources(self, zettel_service):
        """Incoming search on a target returns both notes that link to it."""
        # Arrange
        src1 = _note(zettel_service, "Source 1")
        src2 = _note(zettel_service, "Source 2")
        target = _note(zettel_service, "Common Target")
        zettel_service.create_link(src1.id, target.id, LinkType.REFERENCE)
        zettel_service.create_link(src2.id, target.id, LinkType.SUPPORTS)

        # Act
        results = zettel_service.get_linked_notes(target.id, "incoming")

        # Assert
        result_ids = {n.id for n in results}
        assert result_ids == {src1.id, src2.id}, (
            f"Expected {{src1, src2}} for incoming, got {result_ids}"
        )


# ---------------------------------------------------------------------------
# Orphan detection
# ---------------------------------------------------------------------------

class TestFindOrphanedNotes:
    """find_orphaned_notes() returns notes with no link in either direction."""

    def test_linked_notes_are_excluded_from_orphans(self, zettel_service, search_service):
        """Only the isolated note appears in orphan results; linked notes are excluded."""
        # Arrange
        orphan = _note(zettel_service, "Isolated Orphan", tags=["orphan"])
        connected1 = _note(zettel_service, "Connected 1")
        connected2 = _note(zettel_service, "Connected 2")
        zettel_service.create_link(connected1.id, connected2.id)

        # Act
        orphans = search_service.find_orphaned_notes()

        # Assert
        orphan_ids = {n.id for n in orphans}
        assert orphan.id in orphan_ids, "Isolated note should appear in orphan results"
        assert connected1.id not in orphan_ids, "connected1 has outgoing link, should not be orphan"
        assert connected2.id not in orphan_ids, "connected2 has incoming link, should not be orphan"


# ---------------------------------------------------------------------------
# Central notes ranking
# ---------------------------------------------------------------------------

class TestFindCentralNotes:
    """find_central_notes() orders notes by total connection count."""

    def test_most_connected_note_ranks_first(self, zettel_service, search_service):
        """Hub with 3 links ranks above spokes with 1 link each."""
        # Arrange
        hub = _note(zettel_service, "Hub")
        spoke1 = _note(zettel_service, "Spoke 1")
        spoke2 = _note(zettel_service, "Spoke 2")
        spoke3 = _note(zettel_service, "Spoke 3")
        zettel_service.create_link(hub.id, spoke1.id, LinkType.REFERENCE)
        zettel_service.create_link(hub.id, spoke2.id, LinkType.EXTENDS)
        zettel_service.create_link(hub.id, spoke3.id, LinkType.SUPPORTS)

        # Act
        results = search_service.find_central_notes(limit=10)

        # Assert
        assert len(results) >= 1
        assert results[0][0].id == hub.id, "Hub should rank first with most connections"
        assert results[0][1] == 3, f"Hub should have connection count 3, got {results[0][1]}"

    def test_returns_empty_when_no_notes_have_links(self, zettel_service, search_service):
        """find_central_notes returns [] when no note has any link."""
        # Arrange
        _note(zettel_service, "Isolated")

        # Act / Assert
        assert search_service.find_central_notes() == []


# ---------------------------------------------------------------------------
# Combined search
# ---------------------------------------------------------------------------

class TestSearchCombined:
    """search_combined() — tag + type filtering without FTS."""

    def test_tag_filter_returns_matching_notes(self, zettel_service, search_service):
        """search_combined(tags=[...]) returns all notes tagged with any of the given tags."""
        # Arrange
        note1 = _note(zettel_service, "Python Data Analysis", tags=["python", "data"])
        note2 = _note(zettel_service, "Python Web", tags=["python", "web"])
        _note(zettel_service, "Ruby", tags=["ruby"])

        # Act
        results = search_service.search_combined(tags=["python"])

        # Assert
        result_ids = {r.note.id for r in results}
        assert note1.id in result_ids, "Python Data Analysis should match tag 'python'"
        assert note2.id in result_ids, "Python Web should match tag 'python'"

    def test_tag_and_type_filter_narrows_results(self, zettel_service, search_service):
        """search_combined(tags+note_type) ANDs both filters."""
        # Arrange
        permanent = _note(zettel_service, "Permanent Python", tags=["python"], note_type=NoteType.PERMANENT)
        _note(zettel_service, "Fleeting Python", tags=["python"], note_type=NoteType.FLEETING)

        # Act
        results = search_service.search_combined(tags=["python"], note_type=NoteType.PERMANENT)

        # Assert
        result_ids = {r.note.id for r in results}
        assert permanent.id in result_ids
        assert all(
            r.note.note_type == NoteType.PERMANENT for r in results
        ), "All results should be PERMANENT type"
