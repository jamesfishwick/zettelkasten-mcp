"""Tests for dual-storage synchronization correctness."""
from unittest.mock import patch
import pytest
from slipbox_mcp.models.schema import Note, NoteType, Tag


class TestCreateAtomicity:
    """Verify create() keeps file and DB in sync under failure."""

    def test_db_failure_rolls_back_file(self, note_repository):
        """If DB indexing fails after file write, the file should be cleaned up."""
        note = Note(
            title="Atomicity Test",
            content="This note tests create atomicity.",
            note_type=NoteType.PERMANENT,
            tags=[Tag(name="test")],
        )

        with patch.object(
            note_repository, "_index_note", side_effect=RuntimeError("DB boom")
        ):
            with pytest.raises(RuntimeError, match="DB boom"):
                note_repository.create(note)

        # File should NOT exist if DB failed
        file_path = note_repository.notes_dir / f"{note.id}.md"
        assert not file_path.exists(), "Orphaned file left after DB failure"

        # DB should have no record either
        from sqlalchemy import select
        from slipbox_mcp.models.db_models import DBNote
        with note_repository.session_factory() as session:
            assert session.scalar(select(DBNote).where(DBNote.id == note.id)) is None
