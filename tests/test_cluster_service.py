# tests/test_cluster_service.py
"""Tests for the ClusterService cluster detection algorithms."""
import datetime
import pytest

from zettelkasten_mcp.models.schema import Link, LinkType, Note, NoteType, Tag
from zettelkasten_mcp.services.cluster_service import (
    CO_OCCURRENCE_THRESHOLD,
    MIN_CLUSTER_SIZE,
    ClusterService,
)


def _make_note(
    note_id: str,
    title: str,
    tags: list[str],
    links: list[str] | None = None,
    note_type: NoteType = NoteType.PERMANENT,
) -> Note:
    """Build a minimal Note domain object for testing."""
    now = datetime.datetime.now()
    domain_links = [
        Link(
            source_id=note_id,
            target_id=target,
            link_type=LinkType.REFERENCE,
            created_at=now,
        )
        for target in (links or [])
    ]
    return Note(
        id=note_id,
        title=title,
        content="",
        note_type=note_type,
        tags=[Tag(name=t) for t in tags],
        links=domain_links,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def service(zettel_service):
    return ClusterService(zettel_service=zettel_service)


class TestBuildTagCooccurrence:
    """build_tag_cooccurrence: counts tag pairs that appear together."""

    def test_single_note_pair_counts_once(self, service):
        notes = [_make_note("n1", "A", ["x", "y"])]
        result = service.build_tag_cooccurrence(notes)
        # Pair appears once — below threshold, filtered out.
        assert ("x", "y") not in result

    def test_pair_above_threshold_is_included(self, service):
        notes = [
            _make_note(f"n{i}", f"Note {i}", ["x", "y"])
            for i in range(CO_OCCURRENCE_THRESHOLD)
        ]
        result = service.build_tag_cooccurrence(notes)
        assert ("x", "y") in result
        assert result[("x", "y")] == CO_OCCURRENCE_THRESHOLD

    def test_pair_count_reflects_frequency(self, service):
        notes = [_make_note(f"n{i}", f"Note {i}", ["a", "b"]) for i in range(5)]
        result = service.build_tag_cooccurrence(notes)
        assert result[("a", "b")] == 5

    def test_notes_with_no_tags_produce_no_pairs(self, service):
        notes = [_make_note("n1", "A", []), _make_note("n2", "B", [])]
        assert service.build_tag_cooccurrence(notes) == {}

    def test_single_tag_note_produces_no_pairs(self, service):
        notes = [_make_note(f"n{i}", f"Note {i}", ["solo"]) for i in range(10)]
        assert service.build_tag_cooccurrence(notes) == {}


class TestFindTagClusters:
    """find_tag_clusters: unions tag pairs into connected clusters."""

    def test_two_pairs_sharing_a_tag_merge_into_one_cluster(self, service):
        cooccurrence = {("a", "b"): 5, ("b", "c"): 5}
        clusters = service.find_tag_clusters(cooccurrence)
        assert len(clusters) == 1
        assert clusters[0] == {"a", "b", "c"}

    def test_disjoint_pairs_produce_separate_clusters(self, service):
        cooccurrence = {("a", "b"): 5, ("c", "d"): 5}
        clusters = service.find_tag_clusters(cooccurrence)
        assert len(clusters) == 2

    def test_empty_cooccurrence_returns_empty(self, service):
        assert service.find_tag_clusters({}) == []

    def test_cluster_has_minimum_size_two(self, service):
        # A single pair always satisfies the ≥2 filter.
        cooccurrence = {("x", "y"): 10}
        clusters = service.find_tag_clusters(cooccurrence)
        assert all(len(c) >= 2 for c in clusters)

    def test_higher_frequency_pairs_processed_first(self, service):
        # Three tags where (a,c) is strongest: should merge with whichever side
        # connects them.  Final result is all three in one cluster.
        cooccurrence = {("a", "b"): 3, ("a", "c"): 8, ("b", "c"): 4}
        clusters = service.find_tag_clusters(cooccurrence)
        assert len(clusters) == 1
        assert clusters[0] == {"a", "b", "c"}


class TestCountOrphans:
    """count_orphans: notes with no outgoing links and not a target of any link."""

    def test_note_with_no_links_and_not_targeted_is_orphan(self, service):
        n1 = _make_note("n1", "Orphan", [])
        assert service.count_orphans([n1]) == 1

    def test_note_with_outgoing_link_is_not_orphan(self, service):
        n1 = _make_note("n1", "Source", [], links=["n2"])
        n2 = _make_note("n2", "Target", [])
        assert service.count_orphans([n1, n2]) == 0

    def test_note_that_is_targeted_but_has_no_outgoing_is_not_orphan(self, service):
        n1 = _make_note("n1", "Source", [], links=["n2"])
        n2 = _make_note("n2", "Target", [])  # incoming link from n1
        # n2 has no outgoing links but IS a target — not an orphan
        orphans = service.count_orphans([n1, n2])
        assert orphans == 0

    def test_all_isolated_notes_are_orphans(self, service):
        notes = [_make_note(f"n{i}", f"Note {i}", []) for i in range(5)]
        assert service.count_orphans(notes) == 5

    def test_chain_of_links_produces_no_orphans(self, service):
        n1 = _make_note("n1", "A", [], links=["n2"])
        n2 = _make_note("n2", "B", [], links=["n3"])
        n3 = _make_note("n3", "C", [])
        assert service.count_orphans([n1, n2, n3]) == 0


class TestScoreCluster:
    """score_cluster: returns None for small clusters, dict with score for large ones."""

    def _make_connected_notes(self, count: int) -> list[Note]:
        """Make `count` notes where note 0 links to all others."""
        notes = [_make_note(f"n{i}", f"Note {i}", ["tag-a", "tag-b"]) for i in range(count)]
        # Give note 0 links to all others so they aren't orphans
        targets = [n.id for n in notes[1:]]
        notes[0] = _make_note("n0", "Hub", ["tag-a", "tag-b"], links=targets)
        return notes

    def test_returns_none_for_cluster_below_minimum_size(self, service):
        notes = [_make_note(f"n{i}", f"Note {i}", []) for i in range(MIN_CLUSTER_SIZE - 1)]
        assert service.score_cluster(notes) is None

    def test_returns_dict_for_cluster_at_minimum_size(self, service):
        notes = self._make_connected_notes(MIN_CLUSTER_SIZE)
        result = service.score_cluster(notes)
        assert result is not None
        assert "score" in result
        assert "note_count" in result
        assert "orphan_count" in result
        assert "internal_links" in result
        assert "density" in result
        assert "newest_date" in result

    def test_score_is_bounded_between_zero_and_one(self, service):
        notes = self._make_connected_notes(20)
        result = service.score_cluster(notes)
        assert result is not None
        assert 0.0 <= result["score"] <= 1.0

    def test_all_orphan_cluster_scores_higher_than_well_linked(self, service):
        """Clusters with more orphans should score higher (more urgency)."""
        orphaned = [_make_note(f"n{i}", f"Note {i}", ["x", "y"]) for i in range(10)]
        connected = self._make_connected_notes(10)

        orphan_result = service.score_cluster(orphaned)
        connected_result = service.score_cluster(connected)

        assert orphan_result is not None
        assert connected_result is not None
        assert orphan_result["score"] > connected_result["score"]

    def test_density_is_zero_for_no_internal_links(self, service):
        notes = [_make_note(f"n{i}", f"Note {i}", []) for i in range(MIN_CLUSTER_SIZE)]
        result = service.score_cluster(notes)
        assert result is not None
        assert result["density"] == 0.0


class TestSuggestTitle:
    """suggest_title: generates a title from cluster tags."""

    def test_uses_longest_tag_as_primary(self, service):
        title = service.suggest_title({"ai", "machine-learning", "data"})
        assert title.startswith("Machine Learning")

    def test_single_tag_produces_valid_title(self, service):
        title = service.suggest_title({"python"})
        assert "Python" in title
        assert title.endswith("Knowledge Map")

    def test_hyphen_replaced_by_space_in_title(self, service):
        title = service.suggest_title({"deep-learning"})
        assert "Deep Learning" in title
        assert "-" not in title
