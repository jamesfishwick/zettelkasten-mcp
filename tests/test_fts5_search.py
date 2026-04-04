"""Tests for FTS5-backed search_by_text."""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError
from slipbox_mcp.models.schema import NoteType
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
    zettel_service.create_note(
        title="Unrelated Note",
        content="Nothing to do with the query term at all.",
        tags=["other"]
    )

    results = search_service.search_by_text("epistemology")

    assert len(results) == 2, f"Expected 2 results for 'epistemology', got {len(results)}"
    assert results[0].note.id == high_relevance.id, "Higher-frequency match should rank first"
    assert results[1].note.id == low_relevance.id, f"Expected low-relevance note second, got {results[1].note.id}"
    assert all(r.score > 0 for r in results), "All BM25 scores should be positive"


def test_search_by_text_empty_query(search_service):
    """Empty query must return empty list."""
    assert search_service.search_by_text("") == [], "Empty query should return empty list"


def test_search_by_text_no_matches(zettel_service, search_service):
    """Query with no matches must return empty list."""
    zettel_service.create_note(
        title="Totally Different",
        content="Nothing relevant here.",
        tags=[]
    )
    results = search_service.search_by_text("xyzzyplugh")
    assert results == [], f"Expected no matches for nonsense query, got {results!r}"


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
    assert len(results) == 1, f"Expected 1 title-only match, got {len(results)}"
    assert results[0].note.title == "Phenomenology", f"Expected title 'Phenomenology', got {results[0].note.title!r}"


def test_search_by_text_score_is_positive(zettel_service, search_service):
    """Scores must be positive floats (BM25 negated)."""
    zettel_service.create_note(
        title="Hermeneutics",
        content="The study of interpretation theory.",
        tags=[]
    )
    results = search_service.search_by_text("hermeneutics")
    assert len(results) == 1, f"Expected 1 result for 'hermeneutics', got {len(results)}"
    assert results[0].score > 0, f"Score should be positive, got {results[0].score}"


def test_search_by_text_fts_special_chars_do_not_crash(zettel_service, search_service):
    """FTS5 operator syntax in user input must not cause OperationalError."""
    zettel_service.create_note(
        title="Normal Note",
        content="Some content here.",
        tags=[]
    )
    # These would crash without escaping — verify no exception and a list is returned
    assert isinstance(search_service.search_by_text("AND OR NOT"), list), "FTS5 operators in query should return a list, not crash"
    assert isinstance(search_service.search_by_text('say "hello"'), list), "Quoted strings in query should return a list, not crash"
    assert isinstance(search_service.search_by_text("*wildcard"), list), "Wildcard prefix in query should return a list, not crash"


def test_search_combined_text_uses_bm25(zettel_service, search_service):
    """search_combined with text must return BM25-ranked results, not Python-scored."""
    note_a = zettel_service.create_note(
        title="ontology ontology",
        content="ontology is the branch of metaphysics.",
        note_type=NoteType.PERMANENT,
        tags=["philosophy"]
    )
    zettel_service.create_note(
        title="Brief Mention",
        content="Ontology is mentioned once here.",
        note_type=NoteType.PERMANENT,
        tags=["philosophy"]
    )

    results = search_service.search_combined(query_text="ontology", tags=["philosophy"])

    assert len(results) == 2, f"Expected 2 combined results for 'ontology', got {len(results)}"
    assert results[0].note.id == note_a.id, "Higher BM25 score should rank first"
    assert all(r.score > 0 for r in results), "All combined search scores should be positive"


def test_search_combined_no_text_still_works(zettel_service, search_service):
    """search_combined without text must return all notes matching other filters."""
    note = zettel_service.create_note(
        title="Tagged Note",
        content="Some content.",
        note_type=NoteType.PERMANENT,
        tags=["unique-tag-xyz"]
    )

    results = search_service.search_combined(tags=["unique-tag-xyz"])

    assert len(results) == 1, f"Expected 1 result for unique tag, got {len(results)}"
    assert results[0].note.id == note.id, f"Expected note ID {note.id}, got {results[0].note.id}"
    assert results[0].score == 1.0, f"Expected default score 1.0 without text query, got {results[0].score}"


def test_search_by_text_fts5_operational_error_returns_empty(zettel_service, search_service):
    """An FTS5 OperationalError must return [] rather than raise."""
    fts5_err = OperationalError("fts5: syntax error near X", params=None, orig=Exception("fts5: syntax error near X"))
    with patch.object(search_service.zettel_service.repository, "session_factory") as mock_sf:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.side_effect = fts5_err
        mock_sf.return_value = mock_session
        result = search_service.search_by_text("test query")
    assert result == [], f"FTS5 OperationalError should return empty list, got {result!r}"


def test_search_by_text_non_fts5_operational_error_reraises(zettel_service, search_service):
    """A non-FTS5 OperationalError (e.g. schema issue) must re-raise, not swallow."""
    schema_err = OperationalError("no such table: notes", params=None, orig=Exception("no such table: notes"))
    with patch.object(search_service.zettel_service.repository, "session_factory") as mock_sf:
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.execute.side_effect = schema_err
        mock_sf.return_value = mock_session
        with pytest.raises(OperationalError):
            search_service.search_by_text("test query")


def test_search_combined_fts5_operational_error_returns_metadata_fallback(zettel_service, search_service):
    """When FTS5 raises OperationalError, search_combined returns metadata-only results.

    search_combined uses one session block with two execute() calls:
    1. ORM Select query (metadata filter) — must succeed and return real DBNote objects
    2. text() FTS5 query — raises OperationalError to trigger the fallback

    We intercept at the execute() level, routing by SQL type so the metadata
    query uses the real session and only the FTS5 call raises.
    """
    from sqlalchemy.sql.elements import TextClause

    zettel_service.create_note(
        title="Fallback Note",
        content="Content for fallback test.",
        tags=["fallback-tag"],
    )
    fts5_err = OperationalError(
        "fts5: syntax error near X", params=None,
        orig=Exception("fts5: syntax error near X"),
    )

    repository = search_service.zettel_service.repository
    original_factory = repository.session_factory

    # Wrap session.execute: pass ORM queries through to the real session,
    # raise FTS5 error only for text() queries.
    with original_factory() as real_session:
        original_execute = real_session.execute

        def selective_execute(stmt, *args, **kwargs):
            if isinstance(stmt, TextClause):
                raise fts5_err
            return original_execute(stmt, *args, **kwargs)

        with patch.object(real_session, "execute", side_effect=selective_execute):
            with patch.object(repository, "session_factory", return_value=real_session):
                result = search_service.search_combined(
                    query_text="fallback query", tags=["fallback-tag"]
                )

    assert isinstance(result, list), f"Expected list from fallback, got {type(result)}"
    assert len(result) >= 1, "Fallback must return at least the metadata-matched note"
    assert all(r.score == 0.0 for r in result), "Fallback results should have score 0.0"
    assert all("text search unavailable" in r.matched_context for r in result), "Fallback context should mention text search unavailable"
    assert all(r.matched_terms == set() for r in result), "Fallback results should have empty matched_terms"
