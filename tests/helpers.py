"""Shared test helper utilities (not pytest fixtures)."""
from typing import List, Optional
from slipbox_mcp.models.schema import Note, NoteType, Tag


def make_note(
    title: str = "Test Note",
    content: str = "Test content.",
    note_type: NoteType = NoteType.PERMANENT,
    tags: Optional[List[str]] = None,
    references: Optional[List[str]] = None,
) -> Note:
    """Build a Note domain object with sensible test defaults.

    Override only what the test cares about:

        note = make_note(title="Python", tags=["python", "programming"])
    """
    return Note(
        title=title,
        content=content,
        note_type=note_type,
        tags=[Tag(name=t) for t in (tags or [])],
        references=references or [],
    )
