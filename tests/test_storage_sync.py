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


class TestDeleteAtomicity:
    """Verify delete() keeps file and DB in sync under failure."""

    def test_db_failure_after_file_delete_raises(self, note_repository, zettel_service):
        """If DB delete fails after file removal, the error should propagate."""
        note = zettel_service.create_note(
            title="Delete Sync Test",
            content="Testing delete atomicity.",
        )
        note_id = note.id

        # Verify file exists
        file_path = note_repository.notes_dir / f"{note_id}.md"
        assert file_path.exists()

        with patch.object(
            note_repository, "session_factory", side_effect=RuntimeError("DB down")
        ):
            with pytest.raises(RuntimeError, match="DB down"):
                note_repository.delete(note_id)

        # File should be gone (delete succeeded at file level)
        assert not file_path.exists()

    def test_delete_cleans_db_on_success(self, note_repository, zettel_service):
        """Normal delete removes both file and DB record."""
        note = zettel_service.create_note(
            title="Normal Delete",
            content="Should be fully removed.",
        )
        note_id = note.id

        note_repository.delete(note_id)

        # Both file and DB should be gone
        file_path = note_repository.notes_dir / f"{note_id}.md"
        assert not file_path.exists()

        from sqlalchemy import select
        from slipbox_mcp.models.db_models import DBNote
        with note_repository.session_factory() as session:
            assert session.scalar(select(DBNote).where(DBNote.id == note_id)) is None


class TestUpdateAtomicity:
    """Verify update() keeps file and DB in sync under failure."""

    def test_db_failure_rolls_back_file_change(self, note_repository, zettel_service):
        """If DB update fails, file should revert to previous content."""
        note = zettel_service.create_note(
            title="Original Title",
            content="Original content.",
        )
        note_id = note.id

        # Read original file content
        file_path = note_repository.notes_dir / f"{note_id}.md"
        original_content = file_path.read_text()

        # Attempt update that will fail at DB layer
        note.title = "Updated Title"
        note.content = "Updated content."

        with patch.object(
            note_repository, "session_factory", side_effect=RuntimeError("DB boom")
        ):
            with pytest.raises(RuntimeError, match="DB boom"):
                note_repository.update(note)

        # File should be reverted to original
        assert file_path.read_text() == original_content


class TestLockScope:
    """Verify file_lock covers both file and DB operations."""

    def test_create_holds_lock_during_db_write(self, note_repository):
        """file_lock should be held during _index_note, not just file write."""
        lock_held_during_index = []

        original_index = note_repository._index_note

        def tracking_index(note):
            lock_held_during_index.append(note_repository.file_lock.locked())
            return original_index(note)

        note = Note(
            title="Lock Scope Test",
            content="Testing lock scope.",
            note_type=NoteType.PERMANENT,
        )

        with patch.object(note_repository, "_index_note", side_effect=tracking_index):
            note_repository.create(note)

        assert lock_held_during_index == [True], "file_lock was not held during DB indexing"
