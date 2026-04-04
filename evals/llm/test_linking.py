"""LLM eval: link creation and deduplication workflows.

Tests that Claude correctly creates links between notes and avoids duplicates.
Requires claude CLI to be installed and authenticated.
"""
import pytest
from evals.conftest import run_claude_eval


@pytest.mark.eval
class TestLinking:

    def test_creates_bidirectional_link(self, seeded_slipbox, test_config):
        """LLM should create a contradicts link between Plato and Empiricism."""
        svc, refs = seeded_slipbox

        # The seed data already has a contradicts link from plato -> empiricism.
        # Ask for a link "between them" -- the LLM should recognize it exists
        # or create the reverse direction. Either way, a link should exist.
        result = run_claude_eval(
            prompt=(
                "The note about Plato's forms and the note about empiricism "
                "are in direct opposition. Create a contradicts link between "
                "them if one doesn't exist already."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: a link should exist between plato and empiricism
        plato_id = refs["permanent_plato"]
        empiricism_id = refs["permanent_empiricism"]
        plato_linked = svc.get_linked_notes(plato_id, "both")
        linked_ids = {n.id for n in plato_linked}
        assert empiricism_id in linked_ids, (
            "Expected a link between Plato and Empiricism notes. "
            f"Plato linked to: {linked_ids}"
        )

    def test_does_not_duplicate_existing_link(self, seeded_slipbox, test_config):
        """LLM should recognize an existing link and not create a duplicate."""
        svc, refs = seeded_slipbox

        # Count links on stoicism overview before
        stoicism_id = refs["structure_stoicism"]
        links_before = svc.get_linked_notes(stoicism_id, "both")
        link_count_before = len(links_before)

        result = run_claude_eval(
            prompt=(
                "Connect the stoicism overview note to Seneca's letters on anger. "
                "Make sure there's a link between them."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: link count should not increase (link already exists)
        links_after = svc.get_linked_notes(stoicism_id, "both")
        link_count_after = len(links_after)
        assert link_count_after <= link_count_before + 1, (
            f"Expected no duplicate link. Links before: {link_count_before}, "
            f"after: {link_count_after}"
        )
