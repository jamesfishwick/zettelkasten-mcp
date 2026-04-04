"""LLM eval: MCP prompt workflows.

Tests that Claude correctly uses the MCP prompts (knowledge_creation_batch,
knowledge_synthesis, analyze_note) to perform higher-level knowledge workflows.
Requires claude CLI to be installed and authenticated.
"""
import pytest
from evals.conftest import run_claude_eval


@pytest.mark.eval
class TestPrompts:

    def test_knowledge_creation_batch(self, seeded_slipbox, test_config):
        """LLM should process multiple related ideas into the slipbox as a batch."""
        svc, refs = seeded_slipbox
        existing_ids = set(refs.values())

        result = run_claude_eval(
            prompt=(
                "I have several related ideas about the philosophy of mind: "
                "(1) consciousness might be an illusion, "
                "(2) qualia are private by definition, "
                "(3) the hard problem may be a category error. "
                "Process these into my slipbox as a batch."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: at least 2 new notes should be created
        all_notes = svc.get_all_notes()
        new_notes = [n for n in all_notes if n.id not in existing_ids]
        assert len(new_notes) >= 2, (
            f"Expected at least 2 new notes from batch processing, "
            f"found {len(new_notes)}"
        )

        # Grade: new notes should have links between them or to existing notes
        any_linked = False
        for note in new_notes:
            linked = svc.get_linked_notes(note.id, "both")
            if linked:
                any_linked = True
                break
        assert any_linked, (
            "Expected at least some links among the batch-created notes"
        )

    def test_knowledge_synthesis(self, seeded_slipbox, test_config):
        """LLM should synthesize connections between stoicism and epistemology."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "Look at my notes on stoicism and epistemology. Can you find "
                "any bridges or synthesis opportunities between these two areas?"
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention notes from both clusters
        output = result["output"].lower()
        has_stoicism = (
            "stoic" in output or "seneca" in output or "marcus" in output
        )
        has_epistemology = (
            "epistemology" in output or "plato" in output
            or "empiricism" in output or "rationalism" in output
        )
        assert has_stoicism, (
            f"Expected mention of stoicism-related notes. Output: {output[:500]}"
        )
        assert has_epistemology, (
            f"Expected mention of epistemology-related notes. Output: {output[:500]}"
        )

    def test_analyze_note(self, seeded_slipbox, test_config):
        """LLM should analyze a note and suggest improvements."""
        svc, refs = seeded_slipbox

        # The pasta note is an orphan with no links -- a good candidate for analysis
        result = run_claude_eval(
            prompt=(
                "Analyze my note about Best Pasta Recipes for quality. "
                "How can it be improved for my Zettelkasten?"
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention specific improvement suggestions
        output = result["output"].lower()
        improvement_mentions = (
            "link" in output
            or "connect" in output
            or "orphan" in output
            or "isolated" in output
            or "tag" in output
            or "atomic" in output
            or "split" in output
            or "improve" in output
        )
        assert improvement_mentions, (
            f"Expected improvement suggestions in output. Output: {output[:500]}"
        )
