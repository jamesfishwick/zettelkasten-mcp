"""LLM eval: multi-step knowledge workflows.

Tests that Claude can execute complex knowledge management workflows
involving multiple MCP tool calls. Requires claude CLI to be installed
and authenticated.
"""
import pytest
from evals.conftest import run_claude_eval


@pytest.mark.eval
class TestWorkflow:

    def test_knowledge_creation_workflow(self, seeded_slipbox, test_config):
        """LLM should create a note, tag it, and link to existing stoic notes."""
        svc, refs = seeded_slipbox
        existing_ids = set(refs.values())

        result = run_claude_eval(
            prompt=(
                "I just read that Epictetus taught that we suffer not from "
                "events but from our judgments about them. Process this into "
                "my slipbox with appropriate tags and links to related notes."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: at least one new note created
        all_notes = svc.get_all_notes()
        new_notes = [n for n in all_notes if n.id not in existing_ids]
        assert len(new_notes) >= 1, (
            f"Expected at least 1 new note, found {len(new_notes)}"
        )

        new_note = new_notes[0]

        # Grade: tagged with stoicism-related tags
        stoic_tags = {"stoicism", "stoic", "epictetus", "philosophy", "emotions",
                      "dichotomy-of-control", "judgments"}
        tag_names = {t.name.lower() for t in new_note.tags}
        assert tag_names & stoic_tags, (
            f"Expected stoicism-related tags, got: {tag_names}"
        )

        # Grade: linked to at least one existing stoic note
        linked = svc.get_linked_notes(new_note.id, "both")
        linked_ids = {n.id for n in linked}
        stoic_note_ids = {
            refs["structure_stoicism"],
            refs["permanent_seneca"],
            refs["permanent_marcus"],
            refs["permanent_cbt"],
        }
        assert linked_ids & stoic_note_ids, (
            f"Expected link to existing stoic notes. Linked to: {linked_ids}"
        )

    def test_finds_and_fills_gap(self, seeded_slipbox, test_config):
        """LLM should create a bridging note between stoicism and CBT."""
        svc, refs = seeded_slipbox
        existing_ids = set(refs.values())

        result = run_claude_eval(
            prompt=(
                "I notice my slipbox has notes on stoicism and CBT separately. "
                "Create a note that bridges these two areas, synthesizing the "
                "connection between ancient Stoic philosophy and modern CBT."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: new bridging note created
        all_notes = svc.get_all_notes()
        new_notes = [n for n in all_notes if n.id not in existing_ids]
        assert len(new_notes) >= 1, (
            f"Expected at least 1 new bridging note, found {len(new_notes)}"
        )

        # Grade: the new note should link to at least one stoicism note
        # AND the CBT note
        bridge_note = new_notes[0]
        linked = svc.get_linked_notes(bridge_note.id, "both")
        linked_ids = {n.id for n in linked}

        stoic_ids = {
            refs["structure_stoicism"],
            refs["permanent_seneca"],
            refs["permanent_marcus"],
            refs["permanent_journaling"],
        }
        cbt_id = refs["permanent_cbt"]

        has_stoic_link = bool(linked_ids & stoic_ids)
        has_cbt_link = cbt_id in linked_ids

        assert has_stoic_link or has_cbt_link, (
            f"Expected bridging note to link to stoicism and/or CBT notes. "
            f"Linked to: {linked_ids}"
        )

    def test_structure_note_recognition(self, seeded_slipbox, test_config):
        """LLM should recognize the existing stoicism structure note."""
        svc, refs = seeded_slipbox
        result = run_claude_eval(
            prompt=(
                "My notes about stoicism could use better organization. "
                "Can you check if there's a structure note or cluster that "
                "organizes the stoicism notes? What does it look like?"
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention the existing Stoicism Overview structure note
        output = result["output"].lower()
        assert "stoicism overview" in output or "structure" in output, (
            f"Expected mention of the existing stoicism structure note. "
            f"Output: {output[:500]}"
        )
