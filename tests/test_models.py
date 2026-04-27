# tests/test_models.py
"""Tests for the data models used in the Zettelkasten MCP server."""
import datetime
import re
import pytest
from pydantic import ValidationError
from slipbox_mcp.models.schema import Link, LinkType, Note, NoteType, Tag, generate_id

class TestNoteModel:
    """Tests for the Note model."""
    def test_note_creation_populates_all_fields(self):
        """A Note constructed with required fields has expected defaults and values."""
        note = Note(
            title="Test Note",
            content="This is a test note.",
            note_type=NoteType.PERMANENT,
            tags=[Tag(name="test"), Tag(name="example")]
        )

        # Identity and content
        assert note.id is not None, "Note must have an auto-generated ID"
        assert note.title == "Test Note", f"Title mismatch: {note.title!r}"
        assert note.content == "This is a test note.", f"Content mismatch: {note.content!r}"
        assert note.note_type == NoteType.PERMANENT, f"Note type mismatch: {note.note_type!r}"

        # Collections
        assert len(note.tags) == 2, f"Expected 2 tags, got {len(note.tags)}"
        assert note.links == [], "New note should have empty links list"

        # Timestamps
        assert isinstance(note.created_at, datetime.datetime), "created_at must be a datetime"
        assert isinstance(note.updated_at, datetime.datetime), "updated_at must be a datetime"

    def test_note_validation(self):
        """Test note validation for required fields."""
        # Empty title
        with pytest.raises(ValidationError):
            Note(title="", content="Content")
        # Title with only whitespace
        with pytest.raises(ValidationError):
            Note(title="   ", content="Content")
        # Without content - should fail
        with pytest.raises(ValidationError):
            Note(title="Title")

    def test_note_tag_operations(self):
        """add_tag and remove_tag maintain a unique tag set."""
        note = Note(
            title="Tag Test",
            content="Testing tag operations.",
            tags=[Tag(name="initial")]
        )
        assert len(note.tags) == 1, "Should start with 1 tag"

        # Add tag as string
        note.add_tag("test")
        assert len(note.tags) == 2, "String tag should be added"
        assert any(tag.name == "test" for tag in note.tags), "'test' tag missing"

        # Add tag as Tag object
        note.add_tag(Tag(name="another"))
        assert len(note.tags) == 3, "Tag object should be added"
        assert any(tag.name == "another" for tag in note.tags), "'another' tag missing"

        # Add duplicate tag (should be ignored)
        note.add_tag("test")
        assert len(note.tags) == 3, "Duplicate tag should be ignored"

        # Remove tag
        note.remove_tag("test")
        assert len(note.tags) == 2, "Tag should be removed"
        assert all(tag.name != "test" for tag in note.tags), "'test' tag should be gone"

        # Remove tag that doesn't exist (should not error)
        note.remove_tag("nonexistent")
        assert len(note.tags) == 2, "Removing nonexistent tag should be a no-op"

    def test_literature_note_requires_references(self):
        """Literature notes must have at least one reference."""
        with pytest.raises(ValidationError) as exc_info:
            Note(
                title="Quote from a book",
                content="A passage I want to keep.",
                note_type=NoteType.LITERATURE,
            )
        assert "Literature notes must include at least one reference" in str(exc_info.value)

    def test_literature_note_with_references_passes(self):
        """Literature notes with at least one reference are valid."""
        note = Note(
            title="Quote from a book",
            content="A passage I want to keep.",
            note_type=NoteType.LITERATURE,
            references=["Ahrens, S. (2017). How to Take Smart Notes."],
        )
        assert note.note_type == NoteType.LITERATURE
        assert note.references == ["Ahrens, S. (2017). How to Take Smart Notes."]

    def test_non_literature_notes_do_not_require_references(self):
        """Permanent, fleeting, structure, and hub notes have no reference requirement."""
        for note_type in (NoteType.PERMANENT, NoteType.FLEETING,
                          NoteType.STRUCTURE, NoteType.HUB):
            note = Note(
                title=f"A {note_type.value} note",
                content="Some content.",
                note_type=note_type,
            )
            assert note.references == []

    def test_promoting_to_literature_without_references_raises(self):
        """Reassigning note_type to LITERATURE on a refless note must fail."""
        note = Note(
            title="A draft",
            content="Some content.",
            note_type=NoteType.PERMANENT,
        )
        with pytest.raises(ValidationError):
            note.note_type = NoteType.LITERATURE

    def test_references_reject_empty_string_entries(self):
        """A literature note with references=[''] is rejected: an empty
        citation defeats the purpose of the reference field.
        """
        with pytest.raises(ValidationError):
            Note(
                title="Empty ref",
                content="x",
                note_type=NoteType.LITERATURE,
                references=[""],
            )

    def test_references_reject_whitespace_only_entries(self):
        """A literature note with references=['   '] is rejected after
        whitespace stripping reduces it to empty.
        """
        with pytest.raises(ValidationError):
            Note(
                title="Whitespace ref",
                content="x",
                note_type=NoteType.LITERATURE,
                references=["   "],
            )

    def test_references_strip_whitespace_around_valid_entries(self):
        """Valid citations with leading/trailing whitespace are silently
        stripped (housekeeping, not rejection).
        """
        note = Note(
            title="Padded ref",
            content="x",
            note_type=NoteType.LITERATURE,
            references=["  https://example.com/source  "],
        )
        assert note.references == ["https://example.com/source"]

    def test_promoting_to_literature_after_setting_references_passes(self):
        """When references are set first, promotion to LITERATURE is allowed."""
        note = Note(
            title="A draft",
            content="Some content.",
            note_type=NoteType.PERMANENT,
        )
        note.references = ["https://example.com/source"]
        note.note_type = NoteType.LITERATURE
        assert note.note_type == NoteType.LITERATURE

    def test_note_link_operations(self):
        """add_link and remove_link manage the links list correctly."""
        note = Note(
            title="Link Test",
            content="Testing link operations.",
            id="source123"
        )

        # Add link
        note.add_link("target456", LinkType.REFERENCE, "Test link")
        assert len(note.links) == 1, "Should have 1 link after add"
        assert note.links[0].source_id == "source123", "Source ID mismatch"
        assert note.links[0].target_id == "target456", "Target ID mismatch"
        assert note.links[0].link_type == LinkType.REFERENCE, "Link type mismatch"
        assert note.links[0].description == "Test link", "Description mismatch"

        # Add duplicate link (same target + type -> ignored)
        note.add_link("target456", LinkType.REFERENCE)
        assert len(note.links) == 1, "Duplicate link should be ignored"

        # Add link with different type
        note.add_link("target456", LinkType.EXTENDS)
        assert len(note.links) == 2, "Different link type should be allowed"

        # Remove specific link type
        note.remove_link("target456", LinkType.REFERENCE)
        assert len(note.links) == 1, "Only the REFERENCE link should be removed"
        assert note.links[0].link_type == LinkType.EXTENDS, "EXTENDS link should remain"

        # Remove all links to target
        note.remove_link("target456")
        assert len(note.links) == 0, "All links to target should be removed"


class TestLinkModel:
    """Tests for the Link model."""
    def test_link_creation(self):
        """Link created with all fields has expected values and defaults."""
        link = Link(
            source_id="source123",
            target_id="target456",
            link_type=LinkType.REFERENCE,
            description="Test description"
        )
        assert link.source_id == "source123", "Source ID mismatch"
        assert link.target_id == "target456", "Target ID mismatch"
        assert link.link_type == LinkType.REFERENCE, "Link type mismatch"
        assert link.description == "Test description", "Description mismatch"
        assert isinstance(link.created_at, datetime.datetime), "created_at must be a datetime"

    def test_link_validation(self):
        """Test link validation for required fields."""
        # Missing source_id
        with pytest.raises(ValidationError):
            Link(target_id="target456")
        # Missing target_id
        with pytest.raises(ValidationError):
            Link(source_id="source123")
        # Invalid link_type
        with pytest.raises(ValidationError):
            Link(source_id="source123", target_id="target456", link_type="invalid")

    def test_link_immutability(self):
        """Test that Link objects are immutable (frozen model)."""
        link = Link(
            source_id="source123",
            target_id="target456"
        )
        # Attempt to modify frozen model raises ValidationError
        with pytest.raises(ValidationError):
            link.source_id = "newsource"


class TestTagModel:
    """Tests for the Tag model."""
    def test_tag_creation(self):
        """Tag has expected name and string representation."""
        tag = Tag(name="test")
        assert tag.name == "test", "Tag name mismatch"
        assert str(tag) == "test", "Tag __str__ should return the name"

    def test_tag_immutability(self):
        """Test that Tag objects are immutable (frozen model)."""
        tag = Tag(name="test")
        # Attempt to modify frozen model raises ValidationError
        with pytest.raises(ValidationError):
            tag.name = "newname"


class TestHelperFunctions:
    """Tests for helper functions in the schema module."""

    def test_iso8601_id_format(self):
        """Test that generated IDs follow the correct ISO 8601 format with nanosecond precision."""
        # Generate an ID
        id_str = generate_id()
        
        # Verify it matches the expected format: YYYYMMDDTHHMMSSsssssssss
        # Where sssssssss is a 9-digit nanosecond component
        pattern = r'^\d{8}T\d{6}\d{9}$'
        assert re.match(pattern, id_str), f"ID {id_str} does not match expected ISO 8601 basic format"
        
        # Verify the parts make sense
        date_part = id_str[:8]
        separator = id_str[8]
        time_part = id_str[9:15]
        ns_part = id_str[15:]
        
        assert len(date_part) == 8, "Date part should be 8 digits (YYYYMMDD)"
        assert separator == 'T', "Date/time separator should be 'T' per ISO 8601"
        assert len(time_part) == 6, "Time part should be 6 digits (HHMMSS)"
        assert len(ns_part) == 9, "Nanosecond part should be 9 digits"

    def test_iso8601_uniqueness(self):
        """Test that ISO 8601 IDs with nanosecond precision are unique even in rapid succession."""
        # Generate multiple IDs as quickly as possible
        ids = [generate_id() for _ in range(1000)]
        
        # Verify they are all unique
        unique_ids = set(ids)
        assert len(unique_ids) == 1000, "Generated IDs should all be unique"

    def test_iso8601_chronological_sorting(self):
        """Test that ISO 8601 IDs sort chronologically without artificial delays."""
        # Generate multiple IDs in the fastest possible succession
        ids = [generate_id() for _ in range(5)]
        
        # Verify they're all unique
        assert len(set(ids)) == 5, f"Expected 5 unique IDs, got {len(set(ids))}"
        
        # Verify chronological order matches lexicographical sorting
        sorted_ids = sorted(ids)
        assert sorted_ids == ids, "ISO 8601 IDs should sort chronologically"
