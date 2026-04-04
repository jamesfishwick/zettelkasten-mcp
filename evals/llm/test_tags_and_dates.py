"""LLM eval: tag and date query workflows.

Tests that Claude correctly uses MCP tools to query tags and date-based
note listings. Requires claude CLI to be installed and authenticated.
"""
import pytest
from evals.conftest import run_claude_eval


@pytest.mark.eval
class TestTagsAndDates:

    def test_lists_tags(self, seeded_slipbox, test_config):
        """LLM should list tags from the slipbox when asked for an overview."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "What tags am I using in my slipbox? Give me an overview."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention several seed data tags
        output = result["output"].lower()
        expected_tags = ["stoicism", "philosophy", "epistemology"]
        matches = sum(1 for tag in expected_tags if tag in output)
        assert matches >= 2, (
            f"Expected output to mention at least 2 of {expected_tags}. "
            f"Output: {output[:500]}"
        )

    def test_finds_recent_notes(self, seeded_slipbox, test_config):
        """LLM should list recently added notes."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "What notes have I added most recently?"
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention some seed data notes
        output = result["output"].lower()
        # Any of the seed notes would be valid -- they were all created "recently"
        note_mentions = (
            "seneca" in output
            or "marcus" in output
            or "plato" in output
            or "pasta" in output
            or "stoic" in output
            or "epistemology" in output
            or "cbt" in output
        )
        assert note_mentions, (
            f"Expected output to mention seed data notes. Output: {output[:500]}"
        )

    def test_finds_central_notes(self, seeded_slipbox, test_config):
        """LLM should identify the most-connected notes in the slipbox."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "Which notes in my slipbox have the most connections?"
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention hub/structure notes (they have the most links)
        output = result["output"].lower()
        central_mentions = (
            "stoicism overview" in output
            or "philosophy" in output
            or "epistemology overview" in output
            or "hub" in output
            or "structure" in output
            or "seneca" in output
            or "marcus" in output
        )
        assert central_mentions, (
            f"Expected output to mention well-connected notes. Output: {output[:500]}"
        )
