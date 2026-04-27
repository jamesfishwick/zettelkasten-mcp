"""Tests for the NoteRepository class."""
from slipbox_mcp.models.schema import LinkType, NoteType, Tag
from helpers import make_note

# Named reference strings used across multiple tests
LUHMANN_REF = "Luhmann, N. (1992). Communicating with Slip Boxes."
AHRENS_REF = "Ahrens, S. (2017). How to Take Smart Notes."
ECO_REF = "Eco, U. (1977). How to Write a Thesis."

# External note ID format used in rebuild-index tests
EXTERNAL_NOTE_ID = "20260101T120000000000000"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def test_create_note_returns_note_with_id_and_all_fields(note_repository):
    """create() persists a note and returns it with a generated ID and all fields intact."""
    # Arrange
    note = make_note(title="Test Note", content="This is a test note.", tags=["test", "example"])

    # Act
    saved = note_repository.create(note)

    # Assert — identity
    assert saved.id is not None, "Expected a generated note ID"
    assert saved.title == "Test Note", f"Expected title 'Test Note', got {saved.title!r}"
    assert saved.content == "This is a test note.", f"Expected content 'This is a test note.', got {saved.content!r}"
    assert saved.note_type == NoteType.PERMANENT, f"Expected PERMANENT note type, got {saved.note_type}"
    # Assert — tags (order-independent)
    assert {tag.name for tag in saved.tags} == {"test", "example"}, (
        f"Expected tags {{'test', 'example'}}, got {{{', '.join(t.name for t in saved.tags)}}}"
    )


def test_get_note_returns_file_content_with_title_header(note_repository):
    """get() reads from disk; returned content includes the auto-prepended title heading."""
    # Arrange
    note = make_note(title="Get Test Note", content="Body text.", tags=["test", "get"])
    saved = note_repository.create(note)
    EXPECTED_CONTENT = f"# {note.title}\n\n{note.content}"

    # Act
    retrieved = note_repository.get(saved.id)

    # Assert
    assert retrieved is not None, f"Note {saved.id} was not found after creation"
    assert retrieved.id == saved.id, f"Expected ID {saved.id}, got {retrieved.id}"
    assert retrieved.title == "Get Test Note", f"Expected title 'Get Test Note', got {retrieved.title!r}"
    assert retrieved.content.strip() == EXPECTED_CONTENT.strip(), (
        "get() should prepend a '# Title' heading to content"
    )
    assert {tag.name for tag in retrieved.tags} == {"test", "get"}, (
        f"Expected tags {{'test', 'get'}}, got {{{', '.join(t.name for t in retrieved.tags)}}}"
    )


def test_update_note_persists_new_title_content_and_tags(note_repository):
    """update() writes new values; subsequent get() reflects all changes."""
    # Arrange
    saved = note_repository.create(make_note(title="Original", content="Original body.", tags=["old"]))
    saved.title = "Updated Title"
    saved.content = "Updated body."
    saved.tags = [Tag(name="new")]

    # Act
    updated = note_repository.update(saved)
    EXPECTED_CONTENT = f"# {updated.title}\n\n{updated.content}"

    # Assert — via round-trip read
    retrieved = note_repository.get(saved.id)
    assert retrieved is not None, f"Note {saved.id} not found after update"
    assert retrieved.title == "Updated Title", f"Expected title 'Updated Title', got {retrieved.title!r}"
    assert retrieved.content.strip() == EXPECTED_CONTENT.strip(), (
        "Updated content should include title heading"
    )
    assert {tag.name for tag in retrieved.tags} == {"new"}, (
        f"Expected tags {{'new'}}, got {{{', '.join(t.name for t in retrieved.tags)}}}"
    )


def test_delete_note_removes_from_repository(note_repository):
    """delete() removes the note; subsequent get() returns None."""
    # Arrange
    saved = note_repository.create(make_note(title="Delete Me"))

    # Act — verify existence before deletion
    assert note_repository.get(saved.id) is not None, "Note should exist before deletion"
    note_repository.delete(saved.id)

    # Assert
    assert note_repository.get(saved.id) is None, f"Note {saved.id} should be gone after delete()"


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def test_search_by_content_finds_matching_notes(note_repository):
    """search(content=...) returns notes whose title or content matches."""
    # Arrange
    python = note_repository.create(make_note(title="Python Programming", content="Python is versatile.", tags=["python"]))
    data_sci = note_repository.create(make_note(title="Data Science", content="Data science uses Python.", tags=["python"]))
    js = note_repository.create(make_note(title="JavaScript Basics", content="JavaScript for web.", tags=["javascript"]))

    # Act
    results = note_repository.search(content="Python")

    # Assert — both Python notes present, JS note absent
    result_ids = {n.id for n in results}
    assert python.id in result_ids, "Python Programming note should match content='Python'"
    assert data_sci.id in result_ids, "Data Science note should match content='Python'"
    assert js.id not in result_ids, "JavaScript note should not match content='Python'"


def test_search_by_title_finds_exact_title_match(note_repository):
    """search(title=...) returns notes whose title contains the substring."""
    # Arrange
    note_repository.create(make_note(title="Python Programming", tags=["python"]))
    js = note_repository.create(make_note(title="JavaScript Basics", tags=["javascript"]))
    note_repository.create(make_note(title="Data Science", tags=["data"]))

    # Act
    results = note_repository.search(title="JavaScript")

    # Assert
    assert len(results) == 1, f"Expected 1 result, got {len(results)}: {[n.title for n in results]}"
    assert results[0].id == js.id, f"Expected JavaScript note ID {js.id}, got {results[0].id}"


def test_search_by_note_type_filters_correctly(note_repository):
    """search(note_type=...) returns only notes of that type."""
    # Arrange
    note_repository.create(make_note(title="Permanent Note", note_type=NoteType.PERMANENT))
    structure = note_repository.create(make_note(title="Structure Note", note_type=NoteType.STRUCTURE))

    # Act
    results = note_repository.search(note_type=NoteType.STRUCTURE)

    # Assert
    assert len(results) == 1, f"Expected 1 STRUCTURE note, got {len(results)}"
    assert results[0].id == structure.id, f"Expected structure note ID {structure.id}, got {results[0].id}"


def test_find_by_tag_returns_all_tagged_notes(note_repository):
    """find_by_tag() returns every note carrying that tag, no more."""
    # Arrange
    python = note_repository.create(make_note(title="Python", tags=["python", "programming"]))
    js = note_repository.create(make_note(title="JavaScript", tags=["javascript", "programming"]))
    note_repository.create(make_note(title="Data Science", tags=["data"]))

    # Act
    results = note_repository.find_by_tag("programming")

    # Assert
    assert {n.id for n in results} == {python.id, js.id}, (
        f"Expected exactly python+js notes, got: {[n.title for n in results]}"
    )


# ---------------------------------------------------------------------------
# References persistence
# ---------------------------------------------------------------------------

def test_references_survive_get_all(note_repository):
    """References are preserved through the bulk DB read path (get_all → _db_note_to_note)."""
    # Arrange
    created = note_repository.create(make_note(title="Bulk Ref Note", references=[LUHMANN_REF]))

    # Act
    all_notes = note_repository.get_all()
    match = next((n for n in all_notes if n.id == created.id), None)

    # Assert
    assert match is not None, f"Note {created.id} missing from get_all()"
    assert match.references == [LUHMANN_REF], (
        f"Expected [{LUHMANN_REF!r}], got {match.references!r}"
    )


def test_references_survive_search(note_repository):
    """References are preserved through the DB search path (search → _db_note_to_note)."""
    # Arrange
    note_repository.create(make_note(title="Search Ref Note", references=[AHRENS_REF]))

    # Act
    results = note_repository.search(title="Search Ref Note")

    # Assert
    assert len(results) == 1, f"Expected 1 result for 'Search Ref Note', got {len(results)}"
    assert results[0].references == [AHRENS_REF], (
        f"Expected [{AHRENS_REF!r}], got {results[0].references!r}"
    )


def test_references_survive_update(note_repository):
    """References written via update() are returned correctly by subsequent searches."""
    # Arrange
    created = note_repository.create(make_note(title="Update Ref Note", references=[]))

    # Act
    created.references = [ECO_REF]
    note_repository.update(created)
    results = note_repository.search(title="Update Ref Note")

    # Assert
    assert len(results) == 1, f"Expected 1 result for 'Update Ref Note', got {len(results)}"
    assert results[0].references == [ECO_REF], (
        f"Expected [{ECO_REF!r}] after update, got {results[0].references!r}"
    )


# ---------------------------------------------------------------------------
# Rebuild-index heuristic
# ---------------------------------------------------------------------------

def test_rebuild_index_not_triggered_when_db_is_in_sync(note_repository):
    """No rebuild fires when the DB count matches the indexable file count."""
    from unittest.mock import patch
    note_repository.create(make_note(title="Sync Note"))

    with patch.object(note_repository, "rebuild_index") as mock_rebuild:
        note_repository.rebuild_index_if_needed()

    mock_rebuild.assert_not_called()


def test_rebuild_index_triggered_when_valid_external_file_appears(note_repository):
    """A rebuild fires when a new id-bearing markdown file exists outside the repo."""
    from unittest.mock import patch
    note_repository.create(make_note(title="Existing Note"))
    external = note_repository.notes_dir / f"{EXTERNAL_NOTE_ID}.md"
    external.write_text(
        f"---\nid: {EXTERNAL_NOTE_ID}\ntitle: External\n---\nbody\n"
    )

    with patch.object(note_repository, "rebuild_index") as mock_rebuild:
        note_repository.rebuild_index_if_needed()

    mock_rebuild.assert_called_once()


def test_rebuild_index_not_triggered_for_files_without_frontmatter_id(note_repository):
    """Non-note .md files (no frontmatter id) do not cause a spurious rebuild."""
    from unittest.mock import patch
    note_repository.create(make_note(title="Valid Note"))
    readme = note_repository.notes_dir / "README.md"
    readme.write_text("# README\n\nNo frontmatter id here.\n")

    with patch.object(note_repository, "rebuild_index") as mock_rebuild:
        note_repository.rebuild_index_if_needed()

    mock_rebuild.assert_not_called()


# ---------------------------------------------------------------------------
# Linking
# ---------------------------------------------------------------------------

def test_create_link_between_notes_is_persisted(note_repository):
    """add_link() + update() creates a retrievable outgoing link on the source note."""
    # Arrange
    source = note_repository.create(make_note(title="Source Note", tags=["source"]))
    target = note_repository.create(make_note(title="Target Note", tags=["target"]))

    # Act
    source.add_link(target_id=target.id, link_type=LinkType.REFERENCE, description="A test link")
    updated = note_repository.update(source)

    # Assert — link on returned note
    assert len(updated.links) == 1, f"Expected 1 link on source, got {len(updated.links)}"
    link = updated.links[0]
    assert link.target_id == target.id, f"Expected link target {target.id}, got {link.target_id}"
    assert link.link_type == LinkType.REFERENCE, f"Expected REFERENCE link type, got {link.link_type}"
    assert link.description == "A test link", f"Expected description 'A test link', got {link.description!r}"

    # Assert — link survives a fresh read
    linked = note_repository.find_linked_notes(source.id, "outgoing")
    assert len(linked) == 1, f"Expected 1 outgoing note, got {len(linked)}"
    assert linked[0].id == target.id, f"Expected linked note {target.id}, got {linked[0].id}"


# ---------------------------------------------------------------------------
# Schema-violating hydration: model_construct fallback for legacy data
# ---------------------------------------------------------------------------

def test_get_all_includes_refless_literature_via_model_construct_fallback(note_repository):
    """Legacy literature notes with empty references in storage must remain
    visible to queries. The new model_validator would reject them at strict
    construction, so hydration paths fall back to model_construct and surface
    the violation via the audit-references CLI rather than silently dropping
    the row from query results.
    """
    import datetime
    import json
    from slipbox_mcp.models.db_models import DBNote

    # Inject a refless literature row directly, bypassing the service layer
    # (which would correctly refuse to write this state).
    with note_repository.session_factory() as session:
        bad = DBNote(
            id="20260101T000000000000999",
            title="Legacy literature, missing refs",
            content="Body text from before the validator landed.",
            note_type="literature",
            references_json=json.dumps([]),
            created_at=datetime.datetime(2025, 1, 1, 0, 0, 0),
            updated_at=datetime.datetime(2025, 1, 1, 0, 0, 0),
        )
        session.add(bad)
        session.commit()

    notes = note_repository.get_all()
    found = [n for n in notes if n.id == "20260101T000000000000999"]
    assert len(found) == 1, (
        f"Refless literature note must remain visible to get_all(); "
        f"got {len(found)} matches out of {len(notes)} notes."
    )
    assert found[0].note_type == NoteType.LITERATURE
    assert found[0].references == []
