"""LLM eval: search and discovery workflows.

Tests that Claude correctly uses MCP tools to find and surface information
from the slipbox. Requires claude CLI to be installed and authenticated.
"""
import pytest
from evals.conftest import run_claude_eval


@pytest.mark.eval
class TestSearch:

    def test_finds_notes_by_topic(self, seeded_slipbox, test_config):
        """LLM should find epistemology-related notes when asked."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "What notes do I have about epistemology? "
                "List them with their titles."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention at least 2 of the 3 epistemology-related notes
        # (Plato's Forms, Empiricism vs Rationalism, Epistemology Overview)
        output = result["output"].lower()
        mentions = sum([
            "plato" in output or "forms" in output,
            "empiricism" in output or "rationalism" in output,
            "epistemology overview" in output or "epistemology" in output,
        ])
        assert mentions >= 2, (
            f"Expected output to mention at least 2 epistemology-related notes, "
            f"found {mentions}. Output: {output[:500]}"
        )

    def test_finds_connections_between_topics(self, seeded_slipbox, test_config):
        """LLM should identify connections between stoicism and psychology."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "How does stoicism connect to psychology in my slipbox? "
                "Trace the connections between these topics."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention the CBT note and at least one stoicism note
        output = result["output"].lower()
        assert "cbt" in output or "cognitive behavioral" in output, (
            f"Expected mention of CBT note. Output: {output[:500]}"
        )
        stoic_mentions = (
            "seneca" in output
            or "marcus" in output
            or "stoic" in output
            or "epictetus" in output
        )
        assert stoic_mentions, (
            f"Expected mention of stoicism-related note. Output: {output[:500]}"
        )

    def test_identifies_orphan_notes(self, seeded_slipbox, test_config):
        """LLM should find the unconnected pasta recipe note."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "Are there any isolated notes in my slipbox that aren't "
                "connected to anything? Find orphan notes."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention the pasta recipe orphan
        output = result["output"].lower()
        assert "pasta" in output or "recipe" in output or "cooking" in output, (
            f"Expected mention of the pasta recipe orphan note. Output: {output[:500]}"
        )
