"""Service for searching and discovering notes in the Zettelkasten."""
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import List, Optional, Set, Tuple, Union

from sqlalchemy import or_, select, text
from sqlalchemy.exc import OperationalError

from slipbox_mcp.models.db_models import DBLink, DBNote, DBTag
from slipbox_mcp.models.schema import Note, NoteType
from slipbox_mcp.services.zettel_service import ZettelService
from slipbox_mcp.storage.note_repository import _NOTE_EAGER_LOADS

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """A search result with a note and its relevance score."""
    note: Note
    score: float
    matched_terms: Set[str]
    matched_context: str

class SearchService:
    """Service for searching notes in the Zettelkasten."""

    def __init__(self, zettel_service: Optional[ZettelService] = None):
        self.zettel_service = zettel_service or ZettelService()

    def _run_fts5_query(self, fts_query: str) -> list:
        """Execute an FTS5 MATCH query and return raw result rows.

        Returns list of rows with (id, bm25_score, matched_context).
        Returns [] on FTS5 syntax errors. Re-raises on missing tables.
        """
        repository = self.zettel_service.repository
        sql = text("""
            SELECT
                n.id,
                bm25(notes_fts) AS bm25_score,
                snippet(notes_fts, 1, '', '', '...', 8) AS matched_context
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.rowid
            WHERE notes_fts MATCH :query
            ORDER BY bm25(notes_fts)
        """)
        with repository.session_factory() as session:
            try:
                return session.execute(sql, {"query": fts_query}).fetchall()
            except OperationalError as e:
                err = str(e).lower()
                if "no such table" in err:
                    if "notes_fts" in err:
                        logger.error("FTS5 table 'notes_fts' missing -- run zk_rebuild_index: %s", e)
                    else:
                        logger.error("Required table missing from database schema: %s", e)
                    raise
                if "fts5" in err or ("unterminated string" in err and "notes_fts" in err):
                    logger.warning("FTS5 query syntax error for %r: %s", fts_query, e)
                    return []
                raise

    def search_by_text(
        self, query: str, include_content: bool = True, include_title: bool = True
    ) -> List[SearchResult]:
        """Search for notes by text using SQLite FTS5 with BM25 ranking."""
        if not query:
            return []

        repository = self.zettel_service.repository

        escaped = query.replace('"', '""')
        if include_title and include_content:
            fts_query = f'"{escaped}"'
        elif include_title:
            fts_query = f'title:"{escaped}"'
        else:
            fts_query = f'content:"{escaped}"'

        rows = self._run_fts5_query(fts_query)

        results = []
        for row in rows:
            note = repository.get(row.id)
            if note is None:
                continue
            # bm25() returns negative float; negate so higher = better
            score = -row.bm25_score
            results.append(SearchResult(
                note=note,
                score=score,
                matched_terms=set(query.split()),
                matched_context=f"Content: ...{row.matched_context}...",
            ))

        return results

    def search_by_tag(self, tags: Union[str, List[str]]) -> List[Note]:
        """Search for notes by tags."""
        if isinstance(tags, str):
            return self.zettel_service.get_notes_by_tag(tags)
        return self.zettel_service.repository.search(tags=tags)

    def search_by_link(self, note_id: str, direction: str = "both") -> List[Note]:
        """Search for notes linked to/from a note."""
        return self.zettel_service.get_linked_notes(note_id, direction)

    def find_orphaned_notes(self) -> List[Note]:
        """Find notes with no incoming or outgoing links."""
        return self.zettel_service.repository.find_orphaned_notes()

    def find_central_notes(self, limit: int = 10) -> List[Tuple[Note, int]]:
        """Find notes with the most connections (incoming + outgoing links)."""
        return self.zettel_service.repository.find_central_notes(limit)

    def find_notes_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_updated: bool = False
    ) -> List[Note]:
        """Find notes created or updated within a date range."""
        date_col = DBNote.updated_at if use_updated else DBNote.created_at
        repository = self.zettel_service.repository

        with repository.session_factory() as session:
            query = select(DBNote).options(*_NOTE_EAGER_LOADS)
            if start_date:
                query = query.where(date_col >= start_date)
            if end_date:
                query = query.where(date_col <= end_date)
            query = query.order_by(date_col.desc())

            result = session.execute(query)
            db_notes = result.unique().scalars().all()
            return [repository._db_note_to_note(db_note) for db_note in db_notes]

    def find_similar_notes(self, note_id: str) -> List[Tuple[Note, float]]:
        """Find notes similar to the given note based on shared tags and links."""
        return self.zettel_service.find_similar_notes(note_id)

    def search_combined(
        self,
        query_text: Optional[str] = None,
        tags: Optional[List[str]] = None,
        note_type: Optional[NoteType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[SearchResult]:
        """Perform a combined search: SQL pre-filter by metadata, FTS5 for text ranking."""
        repository = self.zettel_service.repository

        with repository.session_factory() as session:
            query = select(DBNote).options(*_NOTE_EAGER_LOADS)
            if note_type:
                query = query.where(DBNote.note_type == note_type.value)
            if start_date:
                query = query.where(DBNote.created_at >= start_date)
            if end_date:
                query = query.where(DBNote.created_at <= end_date)
            if tags:
                query = query.where(DBNote.tags.any(DBTag.name.in_(tags)))

            db_notes = session.execute(query).unique().scalars().all()
            candidate_ids = {db_note.id: db_note for db_note in db_notes}

            if not query_text:
                notes = [repository._db_note_to_note(n) for n in db_notes]
                return [
                    SearchResult(note=n, score=1.0, matched_terms=set(), matched_context="")
                    for n in notes
                ]

            escaped = query_text.replace('"', '""')
            fts_query = f'"{escaped}"'

        fts_rows = self._run_fts5_query(fts_query)

        results = []
        for row in fts_rows:
            if row.id not in candidate_ids:
                continue
            note = repository._db_note_to_note(candidate_ids[row.id])
            score = -row.bm25_score
            results.append(SearchResult(
                note=note,
                score=score,
                matched_terms=set(query_text.split()),
                matched_context=f"Content: ...{row.matched_context}...",
            ))

        return results
