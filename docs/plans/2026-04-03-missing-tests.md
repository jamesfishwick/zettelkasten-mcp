# Missing Test Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise test coverage from 58% to ~80%+ by adding tests for cluster_service, utils, and uncovered MCP server tool/resource/prompt handlers.

**Architecture:** Three new test files + additions to existing test_mcp_server.py. All new tests follow the refine-tests guidelines: AAA pattern, factory methods via existing `make_note` helper, named constants, assertion messages, precise assertions.

**Tech Stack:** pytest, unittest.mock, existing conftest fixtures

---

### Task 1: Test utils.py

**Files:**
- Create: `tests/test_utils.py`

**Step 1: Write the tests**

```python
"""Tests for utility functions."""
import logging
from datetime import datetime
from unittest.mock import MagicMock

from slipbox_mcp.utils import format_note_for_display, parse_tags, setup_logging


# ---------------------------------------------------------------------------
# parse_tags
# ---------------------------------------------------------------------------

class TestParseTags:
    """parse_tags splits comma-separated strings into stripped tag lists."""

    def test_comma_separated_tags_are_split_and_stripped(self):
        result = parse_tags("  foo , bar , baz  ")
        assert result == ["foo", "bar", "baz"], f"Expected stripped list, got {result!r}"

    def test_empty_string_returns_empty_list(self):
        assert parse_tags("") == [], "Empty string should produce empty list"

    def test_none_like_empty_returns_empty_list(self):
        # parse_tags checks truthiness, so empty string is the falsy case
        assert parse_tags("") == []

    def test_trailing_comma_does_not_produce_empty_element(self):
        result = parse_tags("alpha, beta,")
        assert result == ["alpha", "beta"], f"Trailing comma should be ignored, got {result!r}"

    def test_single_tag_without_comma(self):
        result = parse_tags("solo")
        assert result == ["solo"]


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------

class TestSetupLogging:
    """setup_logging configures the root logger level and handlers."""

    def test_valid_level_string_sets_numeric_level(self):
        # Act
        setup_logging(level="DEBUG")

        # Assert
        root = logging.getLogger()
        assert root.level == logging.DEBUG, (
            f"Expected DEBUG ({logging.DEBUG}), got {root.level}"
        )

    def test_invalid_level_string_falls_back_to_info(self):
        setup_logging(level="BOGUS")

        root = logging.getLogger()
        assert root.level == logging.INFO, (
            f"Expected INFO ({logging.INFO}) fallback, got {root.level}"
        )


# ---------------------------------------------------------------------------
# format_note_for_display
# ---------------------------------------------------------------------------

class TestFormatNoteForDisplay:
    """format_note_for_display produces a human-readable note string."""

    TITLE = "Test Note"
    NOTE_ID = "20260101T120000000000000"
    CONTENT = "Some content here."
    CREATED = datetime(2026, 1, 1, 12, 0, 0)
    UPDATED = datetime(2026, 1, 1, 13, 0, 0)

    def test_basic_fields_appear_in_output(self):
        result = format_note_for_display(
            title=self.TITLE,
            id=self.NOTE_ID,
            content=self.CONTENT,
            tags=[],
            created_at=self.CREATED,
            updated_at=self.UPDATED,
        )

        assert f"# {self.TITLE}" in result, "Title should appear as markdown heading"
        assert f"ID: {self.NOTE_ID}" in result, "Note ID should appear"
        assert self.CONTENT in result, "Content should appear"

    def test_tags_appear_when_provided(self):
        result = format_note_for_display(
            title=self.TITLE,
            id=self.NOTE_ID,
            content=self.CONTENT,
            tags=["python", "testing"],
            created_at=self.CREATED,
            updated_at=self.UPDATED,
        )

        assert "Tags: python, testing" in result, "Tags should be comma-separated"

    def test_tags_absent_when_empty(self):
        result = format_note_for_display(
            title=self.TITLE,
            id=self.NOTE_ID,
            content=self.CONTENT,
            tags=[],
            created_at=self.CREATED,
            updated_at=self.UPDATED,
        )

        assert "Tags:" not in result, "Tags line should be omitted when empty"

    def test_links_section_with_description(self):
        link = MagicMock()
        link.link_type.value = "extends"
        link.target_id = "target123"
        link.description = "builds on this"

        result = format_note_for_display(
            title=self.TITLE,
            id=self.NOTE_ID,
            content=self.CONTENT,
            tags=[],
            created_at=self.CREATED,
            updated_at=self.UPDATED,
            links=[link],
        )

        assert "## Links" in result, "Links section heading should appear"
        assert "extends" in result, "Link type should appear"
        assert "builds on this" in result, "Link description should appear"

    def test_links_section_without_description(self):
        link = MagicMock()
        link.link_type.value = "reference"
        link.target_id = "target456"
        link.description = None

        result = format_note_for_display(
            title=self.TITLE,
            id=self.NOTE_ID,
            content=self.CONTENT,
            tags=[],
            created_at=self.CREATED,
            updated_at=self.UPDATED,
            links=[link],
        )

        assert "reference: target456" in result
        assert "builds on this" not in result  # no description line
```

**Step 2: Run tests**

Run: `pytest tests/test_utils.py -v`
Expected: all PASS

**Step 3: Commit**

```bash
git add tests/test_utils.py
git commit -m "test: add coverage for utils module (parse_tags, setup_logging, format_note)"
```

---

### Task 2: Test cluster_service.py pure functions

**Files:**
- Create: `tests/test_cluster_service.py`

**Step 1: Write the tests**

Uses `make_note` from `tests/helpers.py` and builds notes with tags/links as needed. All cluster service methods are pure functions operating on Note lists -- no DB required.

```python
"""Tests for the cluster detection service."""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from slipbox_mcp.models.schema import Link, LinkType, Note, NoteType, Tag
from slipbox_mcp.services.cluster_service import (
    CO_OCCURRENCE_THRESHOLD,
    MIN_CLUSTER_SIZE,
    ClusterService,
)
from tests.helpers import make_note


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tag(name: str) -> Tag:
    return Tag(name=name)


def _note_with_tags(title: str, tag_names: list[str], **kwargs) -> Note:
    """Build a Note with the given tags.  Accepts extra kwargs for make_note."""
    return make_note(title=title, tags=tag_names, **kwargs)


def _note_with_links(title: str, tag_names: list[str], targets: list[str]) -> Note:
    """Build a Note with tags AND outgoing links."""
    note = _note_with_tags(title, tag_names)
    for tid in targets:
        note.add_link(tid, LinkType.REFERENCE)
    return note


# ---------------------------------------------------------------------------
# build_tag_cooccurrence
# ---------------------------------------------------------------------------

class TestBuildTagCooccurrence:
    """Counts how often tag pairs appear together across notes."""

    def setup_method(self):
        self.service = ClusterService(zettel_service=MagicMock())

    def test_pair_above_threshold_is_included(self):
        # Arrange -- create enough notes so (a, b) meets CO_OCCURRENCE_THRESHOLD
        notes = [
            _note_with_tags(f"Note {i}", ["a", "b"])
            for i in range(CO_OCCURRENCE_THRESHOLD)
        ]

        # Act
        result = self.service.build_tag_cooccurrence(notes)

        # Assert
        assert ("a", "b") in result, f"Expected ('a','b') in cooccurrence, got {result}"
        assert result[("a", "b")] == CO_OCCURRENCE_THRESHOLD

    def test_pair_below_threshold_is_excluded(self):
        notes = [
            _note_with_tags(f"Note {i}", ["x", "y"])
            for i in range(CO_OCCURRENCE_THRESHOLD - 1)
        ]

        result = self.service.build_tag_cooccurrence(notes)

        assert ("x", "y") not in result, "Below-threshold pair should be filtered out"

    def test_tags_are_sorted_alphabetically_in_key(self):
        """Ensures consistent key ordering regardless of tag order on notes."""
        notes = [
            _note_with_tags(f"Note {i}", ["zebra", "alpha"])
            for i in range(CO_OCCURRENCE_THRESHOLD)
        ]

        result = self.service.build_tag_cooccurrence(notes)

        assert ("alpha", "zebra") in result, "Keys should be alphabetically sorted"
        assert ("zebra", "alpha") not in result


# ---------------------------------------------------------------------------
# find_tag_clusters (union-find)
# ---------------------------------------------------------------------------

class TestFindTagClusters:
    """Groups co-occurring tags into clusters using union-find."""

    def setup_method(self):
        self.service = ClusterService(zettel_service=MagicMock())

    def test_single_pair_forms_cluster(self):
        cooccurrence = {("a", "b"): 5}

        clusters = self.service.find_tag_clusters(cooccurrence)

        assert len(clusters) == 1, f"Expected 1 cluster, got {len(clusters)}"
        assert clusters[0] == {"a", "b"}

    def test_overlapping_pairs_merge_into_one_cluster(self):
        cooccurrence = {("a", "b"): 5, ("b", "c"): 4}

        clusters = self.service.find_tag_clusters(cooccurrence)

        assert len(clusters) == 1, f"Expected merged cluster, got {len(clusters)}"
        assert clusters[0] == {"a", "b", "c"}

    def test_disjoint_pairs_form_separate_clusters(self):
        cooccurrence = {("a", "b"): 5, ("x", "y"): 4}

        clusters = self.service.find_tag_clusters(cooccurrence)

        assert len(clusters) == 2, f"Expected 2 disjoint clusters, got {len(clusters)}"
        cluster_sets = [frozenset(c) for c in clusters]
        assert frozenset({"a", "b"}) in cluster_sets
        assert frozenset({"x", "y"}) in cluster_sets

    def test_empty_cooccurrence_returns_empty(self):
        assert self.service.find_tag_clusters({}) == []


# ---------------------------------------------------------------------------
# get_cluster_notes
# ---------------------------------------------------------------------------

class TestGetClusterNotes:
    """Filters notes having >= 2 tags from the cluster."""

    def setup_method(self):
        self.service = ClusterService(zettel_service=MagicMock())

    def test_note_with_two_matching_tags_included(self):
        note = _note_with_tags("Match", ["a", "b", "c"])
        cluster_tags = {"a", "b"}

        result = self.service.get_cluster_notes([note], cluster_tags)

        assert len(result) == 1, "Note with 2 matching tags should be included"

    def test_note_with_one_matching_tag_excluded(self):
        note = _note_with_tags("Partial", ["a", "z"])
        cluster_tags = {"a", "b"}

        result = self.service.get_cluster_notes([note], cluster_tags)

        assert len(result) == 0, "Note with only 1 matching tag should be excluded"


# ---------------------------------------------------------------------------
# has_structure_note
# ---------------------------------------------------------------------------

class TestHasStructureNote:
    """Checks if a structure note already covers a cluster's tags."""

    def setup_method(self):
        self.service = ClusterService(zettel_service=MagicMock())

    def test_structure_note_with_overlapping_tags_returns_true(self):
        structure = _note_with_tags("Map", ["a", "b"], note_type=NoteType.STRUCTURE)
        cluster_tags = {"a", "b", "c"}

        assert self.service.has_structure_note([structure], cluster_tags) is True

    def test_permanent_note_with_matching_tags_returns_false(self):
        permanent = _note_with_tags("Regular", ["a", "b"])
        cluster_tags = {"a", "b"}

        assert self.service.has_structure_note([permanent], cluster_tags) is False

    def test_structure_note_with_single_overlap_returns_false(self):
        structure = _note_with_tags("Map", ["a", "z"], note_type=NoteType.STRUCTURE)
        cluster_tags = {"a", "b"}

        assert self.service.has_structure_note([structure], cluster_tags) is False


# ---------------------------------------------------------------------------
# count_internal_links / count_orphans
# ---------------------------------------------------------------------------

class TestLinkCounting:
    """Internal link and orphan counting within a cluster."""

    def setup_method(self):
        self.service = ClusterService(zettel_service=MagicMock())

    def test_links_between_cluster_members_are_counted(self):
        n1 = _note_with_links("A", ["t"], targets=["id_B"])
        n2 = make_note(title="B")
        # Override IDs for predictable linking
        object.__setattr__(n2, "id", "id_B")

        count = self.service.count_internal_links([n1, n2])

        assert count == 1, f"Expected 1 internal link, got {count}"

    def test_links_to_external_notes_are_not_counted(self):
        n1 = _note_with_links("A", ["t"], targets=["external_id"])
        n2 = make_note(title="B")

        count = self.service.count_internal_links([n1, n2])

        assert count == 0, "Links to notes outside the cluster should not count"

    def test_orphan_has_no_links_and_is_not_targeted(self):
        orphan = make_note(title="Lonely")
        linked = _note_with_links("Connected", ["t"], targets=["some_id"])

        count = self.service.count_orphans([orphan, linked])

        assert count == 1, f"Expected 1 orphan, got {count}"

    def test_note_targeted_by_another_is_not_orphan(self):
        target = make_note(title="Target")
        source = _note_with_links("Source", ["t"], targets=[target.id])

        count = self.service.count_orphans([target, source])

        # target has no outgoing links but IS targeted by source
        assert count == 0, "Targeted note should not be counted as orphan"


# ---------------------------------------------------------------------------
# score_cluster
# ---------------------------------------------------------------------------

class TestScoreCluster:
    """Cluster scoring formula produces expected ranges."""

    def setup_method(self):
        self.service = ClusterService(zettel_service=MagicMock())

    def test_cluster_below_min_size_returns_none(self):
        notes = [make_note(title=f"N{i}") for i in range(MIN_CLUSTER_SIZE - 1)]

        result = self.service.score_cluster(notes)

        assert result is None, "Clusters below MIN_CLUSTER_SIZE should return None"

    def test_cluster_at_min_size_returns_score_dict(self):
        notes = [make_note(title=f"N{i}") for i in range(MIN_CLUSTER_SIZE)]

        result = self.service.score_cluster(notes)

        assert result is not None, "Cluster at MIN_CLUSTER_SIZE should produce a score"
        assert "score" in result
        assert "note_count" in result
        assert result["note_count"] == MIN_CLUSTER_SIZE

    def test_score_is_clamped_to_one(self):
        # Many orphaned notes with no links = high urgency
        notes = [make_note(title=f"N{i}") for i in range(20)]

        result = self.service.score_cluster(notes)

        assert result["score"] <= 1.0, f"Score should be clamped to 1.0, got {result['score']}"

    def test_density_is_zero_when_no_internal_links(self):
        notes = [make_note(title=f"N{i}") for i in range(MIN_CLUSTER_SIZE)]

        result = self.service.score_cluster(notes)

        assert result["density"] == 0.0, f"Expected density 0.0 with no links, got {result['density']}"


# ---------------------------------------------------------------------------
# suggest_title
# ---------------------------------------------------------------------------

class TestSuggestTitle:
    """Title generation from tag sets."""

    def setup_method(self):
        self.service = ClusterService(zettel_service=MagicMock())

    def test_longest_tag_becomes_primary(self):
        result = self.service.suggest_title({"ai", "machine-learning"})

        assert "Machine Learning" in result, f"Expected 'Machine Learning' in title, got {result!r}"
        assert result.endswith("Knowledge Map")

    def test_hyphens_replaced_with_spaces_and_titlecased(self):
        result = self.service.suggest_title({"deep-learning"})

        assert "Deep Learning" in result
```

**Step 2: Run tests**

Run: `pytest tests/test_cluster_service.py -v`
Expected: all PASS

**Step 3: Commit**

```bash
git add tests/test_cluster_service.py
git commit -m "test: add coverage for cluster_service pure functions"
```

---

### Task 3: Test uncovered MCP server tool handlers

**Files:**
- Modify: `tests/test_mcp_server.py`

Add test classes for the uncovered tools: `slipbox_update_note`, `slipbox_delete_note`, `slipbox_remove_link`, `slipbox_get_linked_notes`, `slipbox_get_all_tags`, `slipbox_find_similar_notes` (happy path), `slipbox_find_central_notes` (happy path), `slipbox_find_orphaned_notes`, `slipbox_list_notes_by_date`, `slipbox_rebuild_index`, `_parse_refs`, and cluster tools.

All follow MockServerBase pattern. Tests for each tool cover:
1. Happy path output format
2. "not found" / empty-result path
3. Service method called with correct args

**Step 1: Write tests** (appended to existing file)

See code in implementation.

**Step 2: Run full suite**

Run: `pytest tests/test_mcp_server.py -v`
Expected: all PASS

**Step 3: Commit**

```bash
git add tests/test_mcp_server.py
git commit -m "test: add coverage for remaining MCP server tool handlers"
```

---

### Task 4: Test MCP server resources and prompts

**Files:**
- Modify: `tests/test_mcp_server.py`

Add tests verifying that prompt and resource functions are registered and return expected content.

**Step 1: Write tests**

Extend MockServerBase to capture `self.mcp.resource` and `self.mcp.prompt` registrations similarly to tools.

**Step 2: Run full suite**

Run: `pytest tests/ -v --cov=slipbox_mcp --cov-report=term-missing`
Expected: coverage >= 75%

**Step 3: Commit**

```bash
git add tests/test_mcp_server.py
git commit -m "test: add coverage for MCP resources and prompts"
```

---

### Task 5: Verify coverage target

Run: `pytest tests/ --cov=slipbox_mcp --cov-report=term-missing`

Target: overall coverage >= 75%, with:
- `cluster_service.py` >= 70%
- `utils.py` >= 80%
- `mcp_server.py` >= 65%
