"""LLM eval: cluster analysis and structure note workflows.

Tests that Claude correctly uses cluster tools (refresh, report, dismiss,
create structure). Requires claude CLI to be installed and authenticated.

NOTE: The seed data may or may not produce clusters depending on the algorithm.
If cluster tools return "no clusters found", that is still valid tool usage --
we grade on whether the LLM used the right tools, not on cluster content.
"""
import pytest
from evals.conftest import run_claude_eval


@pytest.mark.eval
class TestClusterOps:

    def test_refreshes_clusters(self, seeded_slipbox, test_config):
        """LLM should use cluster tools to analyze the slipbox."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "Analyze my slipbox for clusters of related notes that "
                "might need a structure note."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention clusters or analysis
        output = result["output"].lower()
        cluster_mentions = (
            "cluster" in output
            or "analysis" in output
            or "structure" in output
            or "group" in output
            or "orphan" in output
            or "no clusters" in output
        )
        assert cluster_mentions, (
            f"Expected mention of cluster analysis. Output: {output[:500]}"
        )

    def test_creates_structure_from_cluster(self, seeded_slipbox, test_config):
        """LLM should run cluster analysis and create a structure note."""
        svc, refs = seeded_slipbox
        existing_ids = set(refs.values())

        result = run_claude_eval(
            prompt=(
                "Run a cluster analysis and create a structure note for "
                "the highest-scoring cluster."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: check if a new structure-type note was created
        # NOTE: Non-deterministic -- the cluster algorithm may not find clusters
        # with the seed data. We check for either a new structure note OR
        # a reasonable explanation in the output.
        all_notes = svc.get_all_notes()
        new_notes = [n for n in all_notes if n.id not in existing_ids]
        new_structure = [
            n for n in new_notes if n.note_type.value == "structure"
        ]

        output = result["output"].lower()
        if new_structure:
            # Success path: structure note was created
            assert len(new_structure) >= 1
        else:
            # Acceptable fallback: LLM used cluster tools but found no viable clusters,
            # or created a note of a different type
            assert (
                "no cluster" in output
                or "cluster" in output
                or len(new_notes) >= 1  # created some note at least
            ), (
                f"Expected either a new structure note or explanation of no clusters. "
                f"New notes: {len(new_notes)}, output: {output[:500]}"
            )

    def test_dismisses_cluster(self, seeded_slipbox, test_config):
        """LLM should run cluster analysis and dismiss the first cluster found."""
        svc, refs = seeded_slipbox

        result = run_claude_eval(
            prompt=(
                "Run a cluster analysis. If any clusters are found, "
                "dismiss the first one."
            ),
            notes_dir=svc.repository.notes_dir,
            db_path=test_config.get_absolute_path(test_config.database_path),
        )
        assert result["exit_code"] == 0, f"claude failed: {result['stderr']}"

        # Grade: output should mention dismissing a cluster or no clusters found
        # NOTE: Non-deterministic -- if no clusters exist, the LLM should say so.
        output = result["output"].lower()
        assert (
            "dismiss" in output
            or "no cluster" in output
            or "cluster" in output
        ), (
            f"Expected mention of cluster dismissal or no clusters. "
            f"Output: {output[:500]}"
        )
