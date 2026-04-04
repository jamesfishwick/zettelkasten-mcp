"""Tests for the ZettelService class."""
import frontmatter as fm
import pytest
from slipbox_mcp.models.schema import LinkType, NoteType


def test_create_note(zettel_service):
    """create_note returns a note with all fields populated."""
    # Act
    note = zettel_service.create_note(
        title="Service Test Note",
        content="Testing note creation through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "test"]
    )

    # Assert
    assert note.id is not None, "Created note must have a generated ID"
    assert note.title == "Service Test Note", f"Title mismatch: {note.title!r}"
    assert note.content == "Testing note creation through the service.", f"Content mismatch: {note.content!r}"
    assert note.note_type == NoteType.PERMANENT, f"Note type mismatch: {note.note_type!r}"
    assert {tag.name for tag in note.tags} == {"service", "test"}, (
        f"Expected tags {{'service', 'test'}}, got {{{', '.join(t.name for t in note.tags)}}}"
    )


def test_get_note(zettel_service):
    """get_note retrieves a note with title heading prepended to content."""
    # Arrange
    note = zettel_service.create_note(
        title="Service Get Note",
        content="Testing note retrieval through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "get"]
    )

    # Act
    retrieved = zettel_service.get_note(note.id)

    # Assert
    assert retrieved is not None, f"Note {note.id} not found after creation"
    assert retrieved.id == note.id, f"ID mismatch: {retrieved.id!r} != {note.id!r}"
    assert retrieved.title == "Service Get Note", f"Title mismatch: {retrieved.title!r}"
    expected_content = f"# {note.title}\n\n{note.content}"
    assert retrieved.content.strip() == expected_content.strip(), (
        "Retrieved content should include auto-prepended title heading"
    )
    assert {tag.name for tag in retrieved.tags} == {"service", "get"}, f"Tag mismatch: {{{', '.join(t.name for t in retrieved.tags)}}}"


def test_update_note(zettel_service):
    """update_note persists new values visible on subsequent get."""
    # Arrange
    note = zettel_service.create_note(
        title="Service Update Note",
        content="Testing note update through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "update"]
    )

    # Act
    updated = zettel_service.update_note(
        note_id=note.id,
        title="Updated Service Note",
        content="This note has been updated through the service.",
        tags=["service", "updated"]
    )

    # Assert
    assert updated.id == note.id, "Updated note should keep the same ID"
    assert updated.title == "Updated Service Note", f"Title mismatch: {updated.title!r}"
    assert "This note has been updated through the service." in updated.content, f"Expected update text in content: {updated.content!r}"
    assert {tag.name for tag in updated.tags} == {"service", "updated"}, f"Tag mismatch: {{{', '.join(t.name for t in updated.tags)}}}"


def test_delete_note(zettel_service):
    """delete_note removes the note so get_note returns None."""
    # Arrange
    note = zettel_service.create_note(
        title="Service Delete Note",
        content="Testing note deletion through the service.",
        note_type=NoteType.PERMANENT,
        tags=["service", "delete"]
    )
    assert zettel_service.get_note(note.id) is not None, "Note should exist before deletion"

    # Act
    zettel_service.delete_note(note.id)

    # Assert
    assert zettel_service.get_note(note.id) is None, (
        f"Note {note.id} should be gone after delete"
    )


def test_create_link(zettel_service):
    """create_link with bidirectional=True creates forward and inverse links."""
    # Arrange
    source_note = zettel_service.create_note(
        title="Service Source Note",
        content="Testing link creation (source).",
        note_type=NoteType.PERMANENT,
        tags=["service", "link", "source"]
    )
    target_note = zettel_service.create_note(
        title="Service Target Note",
        content="Testing link creation (target).",
        note_type=NoteType.PERMANENT,
        tags=["service", "link", "target"]
    )

    # Act
    source, target = zettel_service.create_link(
        source_id=source_note.id,
        target_id=target_note.id,
        link_type=LinkType.REFERENCE,
        description="A test link via service",
        bidirectional=True
    )

    # Assert -- forward link
    assert len(source.links) == 1, f"Source should have 1 link, got {len(source.links)}"
    assert source.links[0].target_id == target_note.id, f"Forward link target mismatch: {source.links[0].target_id!r}"
    assert source.links[0].link_type == LinkType.REFERENCE, f"Forward link type mismatch: {source.links[0].link_type!r}"
    assert source.links[0].description == "A test link via service", f"Forward link description mismatch: {source.links[0].description!r}"

    # Assert -- inverse link
    assert len(target.links) == 1, f"Target should have 1 inverse link, got {len(target.links)}"
    assert target.links[0].target_id == source_note.id, f"Inverse link target mismatch: {target.links[0].target_id!r}"
    assert target.links[0].link_type == LinkType.REFERENCE, f"Inverse link type mismatch: {target.links[0].link_type!r}"

    # Assert -- traversal
    outgoing = zettel_service.get_linked_notes(source_note.id, "outgoing")
    assert len(outgoing) == 1, f"Expected 1 outgoing link, got {len(outgoing)}"
    assert outgoing[0].id == target_note.id, f"Outgoing note ID mismatch: {outgoing[0].id!r}"

    incoming = zettel_service.get_linked_notes(target_note.id, "incoming")
    assert len(incoming) == 1, f"Expected 1 incoming link, got {len(incoming)}"
    assert incoming[0].id == source_note.id, f"Incoming note ID mismatch: {incoming[0].id!r}"

    both = zettel_service.get_linked_notes(source_note.id, "both")
    assert len(both) == 1, f"Expected 1 'both' link, got {len(both)}"
    assert both[0].id == target_note.id, f"Both-direction note ID mismatch: {both[0].id!r}"


def test_search_notes(zettel_service):
    """Tag search, add_tag, and remove_tag work through the service."""
    # Arrange
    note1 = zettel_service.create_note(
        title="Python Basics",
        content="Introduction to Python programming.",
        note_type=NoteType.PERMANENT,
        tags=["python", "programming", "service"]
    )
    note2 = zettel_service.create_note(
        title="Advanced Python",
        content="Advanced techniques in Python.",
        note_type=NoteType.PERMANENT,
        tags=["python", "advanced", "service"]
    )
    zettel_service.create_note(
        title="JavaScript Introduction",
        content="Basics of JavaScript programming.",
        note_type=NoteType.PERMANENT,
        tags=["javascript", "programming", "service"]
    )

    # Act -- tag search
    python_notes = zettel_service.get_notes_by_tag("python")

    # Assert
    assert len(python_notes) == 2, f"Expected 2 python-tagged notes, got {len(python_notes)}"
    assert {n.id for n in python_notes} == {note1.id, note2.id}, f"Python notes ID mismatch: {{{', '.join(n.id for n in python_notes)}}}"

    # Act -- add/remove tag
    first = python_notes[0]
    zettel_service.add_tag_to_note(first.id, "newTag")
    updated = zettel_service.get_note(first.id)
    assert "newTag" in {tag.name for tag in updated.tags}, "newTag should be present after add"

    zettel_service.remove_tag_from_note(first.id, "newTag")
    updated = zettel_service.get_note(first.id)
    assert "newTag" not in {tag.name for tag in updated.tags}, "newTag should be gone after remove"


def test_find_similar_notes(zettel_service):
    """find_similar_notes returns notes sharing tags or links with the reference note."""
    # Arrange
    note1 = zettel_service.create_note(
        title="Machine Learning Basics",
        content="Introduction to machine learning concepts.",
        note_type=NoteType.PERMANENT,
        tags=["AI", "machine learning", "data science"]
    )
    note2 = zettel_service.create_note(
        title="Neural Networks",
        content="Overview of neural network architectures.",
        note_type=NoteType.PERMANENT,
        tags=["AI", "machine learning", "neural networks"]
    )
    note3 = zettel_service.create_note(
        title="Python for Data Science",
        content="Using Python for data analysis and machine learning.",
        note_type=NoteType.PERMANENT,
        tags=["python", "data science"]
    )
    zettel_service.create_note(
        title="History of Computing",
        content="Evolution of computing technology.",
        note_type=NoteType.PERMANENT,
        tags=["history", "computing"]
    )
    zettel_service.create_link(note1.id, note2.id, LinkType.EXTENDS)
    zettel_service.create_link(note1.id, note3.id, LinkType.REFERENCE)

    # Act
    similar = zettel_service.find_similar_notes(note1.id, 0.0)

    # Assert
    similar_ids = [n.id for n, _ in similar]
    assert len(similar) > 0, "Expected at least one similar note"
    assert note2.id in similar_ids or note3.id in similar_ids, (
        "At least one linked/shared-tag note should appear in similar results"
    )


def test_export_note_returns_yaml_frontmatter(zettel_service):
    """export_note output contains YAML frontmatter matching the on-disk format."""
    # Arrange
    REF = "Ahrens, S. (2017). How to Take Smart Notes."
    note = zettel_service.create_note(
        title="Export Test",
        content="Body text.",
        note_type=NoteType.PERMANENT,
        tags=["export", "test"],
        references=[REF],
    )

    # Act
    result = zettel_service.export_note(note.id)

    # Assert
    post = fm.loads(result)
    assert post.metadata.get("id") == note.id, "id must appear in YAML frontmatter"
    assert post.metadata.get("type") == "permanent", f"Expected type 'permanent', got {post.metadata.get('type')!r}"
    assert set(post.metadata.get("tags", [])) == {"export", "test"}, f"Tag mismatch: {post.metadata.get('tags')!r}"
    assert post.metadata.get("references") == [REF], f"References mismatch: {post.metadata.get('references')!r}"
    assert "Export Test" in post.content, f"Expected 'Export Test' in content: {post.content[:100]!r}"


def test_export_note_includes_links_section(zettel_service):
    """export_note includes ## Links section when links exist."""
    # Arrange
    source = zettel_service.create_note(title="Source", content="Source body.")
    target = zettel_service.create_note(title="Target", content="Target body.")
    zettel_service.create_link(source.id, target.id, LinkType.SUPPORTS, "key evidence")

    # Act
    result = zettel_service.export_note(source.id)

    # Assert
    assert "## Links" in result, "Export should contain Links section"
    assert f"supports [[{target.id}]]" in result, f"Expected supports link in export: {result[:200]!r}"
    assert "key evidence" in result, f"Expected 'key evidence' in export: {result[:200]!r}"


def test_export_note_raises_for_missing_id(zettel_service):
    """export_note raises ValueError for an unknown note ID."""
    with pytest.raises(ValueError, match="not found"):
        zettel_service.export_note("nonexistent-id-000000000")


def test_export_note_round_trips(zettel_service):
    """export_note output parses back to a note with identical fields."""
    # Arrange
    REF = "Ahrens, S. (2017). How to Take Smart Notes."
    note = zettel_service.create_note(
        title="Round-trip Test",
        content="Body text.",
        note_type=NoteType.PERMANENT,
        tags=["round-trip", "test"],
        references=[REF],
    )
    target = zettel_service.create_note(title="Target", content="Target body.")
    zettel_service.create_link(note.id, target.id, LinkType.REFERENCE, "key link")

    # Act
    exported = zettel_service.export_note(note.id)
    parsed = zettel_service.repository._parse_note_from_markdown(exported)

    # Assert
    assert parsed is not None, "Exported markdown should parse back to a Note"
    assert parsed.id == note.id, f"Round-trip ID mismatch: {parsed.id!r} != {note.id!r}"
    assert parsed.note_type == NoteType.PERMANENT, f"Round-trip note type mismatch: {parsed.note_type!r}"
    assert {t.name for t in parsed.tags} == {"round-trip", "test"}, f"Round-trip tag mismatch: {{{', '.join(t.name for t in parsed.tags)}}}"
    assert parsed.references == [REF], f"Round-trip references mismatch: {parsed.references!r}"
    assert len(parsed.links) == 1, f"Expected 1 link after round-trip, got {len(parsed.links)}"
    assert parsed.links[0].target_id == target.id, f"Round-trip link target mismatch: {parsed.links[0].target_id!r}"
    assert parsed.links[0].description == "key link", f"Round-trip link description mismatch: {parsed.links[0].description!r}"
