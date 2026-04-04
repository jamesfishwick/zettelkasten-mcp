"""LLM eval: update and delete workflows.

Tests that Claude correctly uses MCP tools to modify and remove knowledge
in the slipbox. Requires claude CLI to be installed and authenticated.
"""
import pytest
from evals.conftest import run_claude_eval


@pytest.mark.eval
class TestUpdateDelete:

    def test_updates_note_content(self, seeded_slipbox, test_config):
        """LLM should update the existing Seneca note rather than creating a new one."""
        svc, refs = seeded_slipbox
        seneca_id = refs["permanent_seneca"]
        original_note = svc.get_note(seneca_id)
        original_length = len(original_note.content)

        result = run_claude_eval(
            prompt=(
                "My note about Seneca's letters needs updating. Add a paragraph "
                "about Letter 18 on poverty. Don't create a new note."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: the Seneca note's content should have changed (longer than before)
        updated_note = svc.get_note(seneca_id)
        assert updated_note is not None, "Seneca note should still exist"
        assert len(updated_note.content) > original_length, (
            f"Expected Seneca note content to grow. "
            f"Original length: {original_length}, updated: {len(updated_note.content)}"
        )

    def test_deletes_note_when_asked(self, seeded_slipbox, test_config):
        """LLM should delete the specified fleeting note."""
        svc, refs = seeded_slipbox
        note_count_before = len(svc.get_all_notes())
        skepticism_id = refs["fleeting_skepticism"]

        result = run_claude_eval(
            prompt=(
                "Delete my fleeting note about Pyrrhonian skepticism -- "
                "I've already processed it."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: note count decreased and the specific note is gone
        note_count_after = len(svc.get_all_notes())
        assert note_count_after < note_count_before, (
            f"Expected note count to decrease. Before: {note_count_before}, "
            f"after: {note_count_after}"
        )
        deleted_note = svc.get_note(skepticism_id)
        assert deleted_note is None, (
            "The Pyrrhonian skepticism note should have been deleted"
        )

    def test_removes_link_when_asked(self, seeded_slipbox, test_config):
        """LLM should remove the contradicts link between Plato and empiricism."""
        svc, refs = seeded_slipbox
        plato_id = refs["permanent_plato"]
        empiricism_id = refs["permanent_empiricism"]

        # Verify link exists before
        linked_before = svc.get_linked_notes(plato_id, "both")
        linked_ids_before = {n.id for n in linked_before}
        assert empiricism_id in linked_ids_before, "Pre-condition: link should exist"

        result = run_claude_eval(
            prompt=(
                "Remove the link between the Plato forms note and the "
                "empiricism note."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: link should no longer exist
        linked_after = svc.get_linked_notes(plato_id, "both")
        linked_ids_after = {n.id for n in linked_after}
        assert empiricism_id not in linked_ids_after, (
            f"Expected link between Plato and empiricism to be removed. "
            f"Still linked to: {linked_ids_after}"
        )
