"""Tests for FTS5-backed search_by_text."""
import pytest
from slipbox_mcp.models.schema import NoteType, Tag
from slipbox_mcp.services.search_service import SearchService


@pytest.fixture
def search_service(zettel_service):
    return SearchService(zettel_service)


def test_search_by_text_returns_ranked_results(zettel_service, search_service):
    """search_by_text must return results ordered by BM25 relevance."""
    high_relevance = zettel_service.create_note(
        title="epistemology epistemology",
        content="epistemology is the study of knowledge and justified belief.",
        tags=["philosophy"]
    )
    low_relevance = zettel_service.create_note(
        title="Other Philosophy",
        content="This note touches on epistemology briefly.",
        tags=["philosophy"]
    )
    no_match = zettel_service.create_note(
        title="Unrelated Note",
        content="Nothing to do with the query term at all.",
        tags=["other"]
    )

    results = search_service.search_by_text("epistemology")

    assert len(results) == 2
    assert results[0].note.id == high_relevance.id, "Higher-frequency match should rank first"
    assert results[1].note.id == low_relevance.id
    assert all(r.score > 0 for r in results)


def test_search_by_text_empty_query(search_service):
    """Empty query must return empty list."""
    assert search_service.search_by_text("") == []


def test_search_by_text_no_matches(zettel_service, search_service):
    """Query with no matches must return empty list."""
    zettel_service.create_note(
        title="Totally Different",
        content="Nothing relevant here.",
        tags=[]
    )
    results = search_service.search_by_text("xyzzyplugh")
    assert results == []


def test_search_by_text_include_title_only(zettel_service, search_service):
    """include_content=False must only search titles."""
    zettel_service.create_note(
        title="Phenomenology",
        content="Body text without the search term.",
        tags=[]
    )
    zettel_service.create_note(
        title="Unrelated",
        content="phenomenology appears only in the content here.",
        tags=[]
    )

    results = search_service.search_by_text("phenomenology", include_content=False)
    assert len(results) == 1
    assert results[0].note.title == "Phenomenology"


def test_search_by_text_score_is_positive(zettel_service, search_service):
    """Scores must be positive floats (BM25 negated)."""
    zettel_service.create_note(
        title="Hermeneutics",
        content="The study of interpretation theory.",
        tags=[]
    )
    results = search_service.search_by_text("hermeneutics")
    assert len(results) == 1
    assert results[0].score > 0


def test_search_by_text_fts_special_chars_do_not_crash(zettel_service, search_service):
    """FTS5 operator syntax in user input must not cause OperationalError."""
    zettel_service.create_note(
        title="Normal Note",
        content="Some content here.",
        tags=[]
    )
    # These would crash without escaping
    assert search_service.search_by_text("AND OR NOT") == [] or True  # no crash
    assert search_service.search_by_text('say "hello"') == [] or True  # no crash
    assert search_service.search_by_text("*wildcard") == [] or True   # no crash


def test_search_combined_text_uses_bm25(zettel_service, search_service):
    """search_combined with text must return BM25-ranked results, not Python-scored."""
    note_a = zettel_service.create_note(
        title="ontology ontology",
        content="ontology is the branch of metaphysics.",
        note_type=NoteType.PERMANENT,
        tags=["philosophy"]
    )
    note_b = zettel_service.create_note(
        title="Brief Mention",
        content="Ontology is mentioned once here.",
        note_type=NoteType.PERMANENT,
        tags=["philosophy"]
    )

    results = search_service.search_combined(query_text="ontology", tags=["philosophy"])

    assert len(results) == 2
    assert results[0].note.id == note_a.id, "Higher BM25 score should rank first"
    assert all(r.score > 0 for r in results)


def test_search_combined_no_text_still_works(zettel_service, search_service):
    """search_combined without text must return all notes matching other filters."""
    note = zettel_service.create_note(
        title="Tagged Note",
        content="Some content.",
        note_type=NoteType.PERMANENT,
        tags=["unique-tag-xyz"]
    )

    results = search_service.search_combined(tags=["unique-tag-xyz"])

    assert len(results) == 1
    assert results[0].note.id == note.id
    assert results[0].score == 1.0
