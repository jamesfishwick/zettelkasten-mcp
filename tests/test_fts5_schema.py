"""Tests for FTS5 virtual table schema."""
from sqlalchemy import text

def test_fts5_table_exists(note_repository):
    """notes_fts virtual table must exist after init_db."""
    with note_repository.session_factory() as session:
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='notes_fts'")
        ).fetchone()
    assert result is not None, "notes_fts FTS5 virtual table was not created"

def test_fts5_columns(note_repository):
    """notes_fts must index title and content columns."""
    with note_repository.session_factory() as session:
        session.execute(text(
            "INSERT INTO notes_fts(rowid, title, content) VALUES (999999, 'test title', 'test content')"
        ))
        result = session.execute(
            text("SELECT rowid FROM notes_fts WHERE notes_fts MATCH 'test'")
        ).fetchall()
    assert any(row[0] == 999999 for row in result)

def test_fts5_trigger_sync_on_insert(note_repository):
    """Inserting into notes via repository must auto-populate notes_fts via trigger."""
    from slipbox_mcp.models.schema import Note, NoteType, Tag

    note_repository.create(Note(
        title="TriggerSyncTitle",
        content="trigger sync body content",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="trigger-test")]
    ))

    with note_repository.session_factory() as session:
        result = session.execute(
            text("SELECT rowid FROM notes_fts WHERE notes_fts MATCH 'TriggerSyncTitle'")
        ).fetchall()

    assert len(result) == 1

def test_fts5_populated_after_rebuild(note_repository):
    """FTS index must be queryable after rebuild_index runs."""
    from slipbox_mcp.models.schema import Note, NoteType, Tag

    note_repository.create(Note(
        title="Unique Zettelkasten Term",
        content="antidisestablishmentarianism is searchable",
        note_type=NoteType.PERMANENT,
        tags=[Tag(name="test")]
    ))

    note_repository.rebuild_index()

    with note_repository.session_factory() as session:
        results = session.execute(
            text("SELECT rowid FROM notes_fts WHERE notes_fts MATCH 'antidisestablishmentarianism'")
        ).fetchall()

    assert len(results) == 1
