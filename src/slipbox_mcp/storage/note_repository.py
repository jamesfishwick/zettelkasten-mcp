"""Repository for note storage and retrieval."""
import datetime
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, List, Optional, Union

import frontmatter
from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from slipbox_mcp.config import config
from slipbox_mcp.models.db_models import (DBLink, DBNote, DBTag,
                                            get_session_factory, init_db)
from slipbox_mcp.models.schema import Link, LinkType, Note, NoteType, Tag
from slipbox_mcp.storage.base import Repository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Markdown parsing helpers (module-level, no instance state needed)
# ---------------------------------------------------------------------------

def _parse_frontmatter_tags(raw: Any) -> list[Tag]:
    """Parse tags from frontmatter value (str, list, or None)."""
    if isinstance(raw, str):
        tag_names = [t.strip() for t in raw.split(",") if t.strip()]
    elif isinstance(raw, list):
        tag_names = [str(t).strip() for t in raw if str(t).strip()]
    else:
        return []
    return [Tag(name=name) for name in tag_names]


def _parse_links_section(content: str, source_id: str) -> list[Link]:
    """Parse the ``## Links`` block from note content."""
    links: list[Link] = []
    in_links = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## Links"):
            in_links = True
            continue
        if in_links and stripped.startswith("## "):
            in_links = False
            continue
        if in_links and stripped.startswith("- "):
            try:
                if "[[" in stripped and "]]" in stripped:
                    parts = stripped.split("[[", 1)
                    link_type_str = parts[0].strip()
                    if link_type_str.startswith("- "):
                        link_type_str = link_type_str[2:].strip()
                    id_and_desc = parts[1].split("]]", 1)
                    target_id = id_and_desc[0].strip()
                    description = None
                    if len(id_and_desc) > 1:
                        description = id_and_desc[1].strip()
                    try:
                        link_type = LinkType(link_type_str)
                    except ValueError:
                        link_type = LinkType.REFERENCE
                    links.append(
                        Link(
                            source_id=source_id,
                            target_id=target_id,
                            link_type=link_type,
                            description=description,
                            created_at=datetime.datetime.now(),
                        )
                    )
            except Exception as e:
                logger.error("Error parsing link: %s - %s", line, e)
    return links


def _parse_frontmatter_dates(
    metadata: dict[str, Any],
) -> tuple[datetime.datetime, datetime.datetime]:
    """Parse created/updated datetimes from frontmatter metadata."""
    created_str = metadata.get("created")
    created_at = (
        datetime.datetime.fromisoformat(created_str)
        if created_str
        else datetime.datetime.now()
    )
    updated_str = metadata.get("updated")
    updated_at = (
        datetime.datetime.fromisoformat(updated_str)
        if updated_str
        else created_at
    )
    return created_at, updated_at


# Eager-load options applied to every DBNote query to avoid N+1 queries on
# tags, outgoing links, and incoming links.
_NOTE_EAGER_LOADS = [
    joinedload(DBNote.tags),
    joinedload(DBNote.outgoing_links),
    joinedload(DBNote.incoming_links),
]

class NoteRepository(Repository[Note]):
    """Repository for note storage and retrieval.
    This implements a dual storage approach:
    1. Notes are stored as Markdown files on disk for human readability and editing
    2. MySQL database is used for indexing and efficient querying
    The file system is the source of truth - database is rebuilt from files if needed.
    """

    def __init__(self, notes_dir: Optional[Path] = None):
        self.notes_dir = (
            config.get_absolute_path(notes_dir)
            if notes_dir
            else config.get_absolute_path(config.notes_dir)
        )

        self.notes_dir.mkdir(parents=True, exist_ok=True)

        self.engine = init_db()
        self.session_factory = get_session_factory(self.engine)

        self.file_lock = threading.RLock()

        self.rebuild_index_if_needed()

    def rebuild_index_if_needed(self) -> None:
        """Rebuild the database index from files if needed."""
        with self.session_factory() as session:
            db_count = session.scalar(select(text("COUNT(*)")).select_from(DBNote))

        indexable_count = self._count_indexable_files()

        if db_count != indexable_count:
            self.rebuild_index()

    def _count_indexable_files(self) -> int:
        """Count .md files that have a valid frontmatter 'id' field.

        Reads only the frontmatter block (up to the closing '---') of each
        file rather than full content, keeping startup cost low.
        """
        count = 0
        for file_path in self.notes_dir.glob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    header = f.read(2048)
                if not header.startswith("---"):
                    continue
                end = header.find("\n---", 3)
                if end == -1:
                    continue
                frontmatter_block = header[3:end]
                if re.search(r"^id:\s*\S", frontmatter_block, re.MULTILINE):
                    count += 1
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("Could not read %s during indexable count; skipping: %s", file_path, e)
        return count

    def rebuild_index(self) -> None:
        """Rebuild the database index from all markdown files."""
        with self.session_factory() as session:
            session.execute(text("DELETE FROM links"))
            session.execute(text("DELETE FROM note_tags"))
            session.execute(text("DELETE FROM notes"))
            session.commit()

        note_files = list(self.notes_dir.glob("*.md"))

        # Process files in batches to avoid memory issues with large Zettelkasten systems
        batch_size = 100
        for i in range(0, len(note_files), batch_size):
            batch = note_files[i:i + batch_size]
            notes = []

            for file_path in batch:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    note = self._parse_note_from_markdown(content)
                    if note:  # Skip files without IDs
                        notes.append(note)
                except Exception as e:
                    logger.error("Error processing file %s: %s", file_path, e)

            for note in notes:
                self._index_note(note)

        # Rebuild FTS index to ensure consistency after bulk delete + re-insert
        with self.session_factory() as session:
            session.execute(text("INSERT INTO notes_fts(notes_fts) VALUES ('rebuild')"))
            session.commit()

    def _parse_note_from_markdown(self, content: str) -> Optional[Note]:
        """Parse a note from markdown content."""
        post = frontmatter.loads(content)
        metadata = post.metadata

        note_id = metadata.get("id")
        if not note_id:
            return None

        title = metadata.get("title")
        if not title:
            for line in post.content.strip().split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        if not title:
            raise ValueError("Note title missing from frontmatter or content")

        note_type_str = metadata.get("type", NoteType.PERMANENT.value)
        try:
            note_type = NoteType(note_type_str)
        except ValueError:
            note_type = NoteType.PERMANENT

        tags = _parse_frontmatter_tags(metadata.get("tags", ""))
        links = _parse_links_section(post.content, source_id=note_id)
        created_at, updated_at = _parse_frontmatter_dates(metadata)

        refs_raw = metadata.get("references", [])
        if isinstance(refs_raw, list):
            references = [str(r) for r in refs_raw if str(r).strip()]
        elif isinstance(refs_raw, str):
            references = [r.strip() for r in refs_raw.split("\n") if r.strip()]
        else:
            references = []

        return Note(
            id=note_id,
            title=title,
            content=post.content,
            note_type=note_type,
            tags=tags,
            links=links,
            references=references,
            created_at=created_at,
            updated_at=updated_at,
            metadata={k: v for k, v in metadata.items()
                     if k not in ["id", "title", "type", "tags", "created", "updated", "references"]}
        )

    def _db_note_to_note(self, db_note: DBNote) -> Note:
        """Convert a DBNote (with eager-loaded relationships) to a domain Note.

        Avoids per-note file I/O by using data already loaded from the database.
        Requires that db_note.tags, db_note.outgoing_links, and
        db_note.incoming_links have been eager-loaded in the calling query.
        """
        tags = [Tag(name=t.name) for t in db_note.tags]
        links = [
            Link(
                source_id=lnk.source_id,
                target_id=lnk.target_id,
                link_type=LinkType(lnk.link_type),
                description=lnk.description,
                created_at=lnk.created_at,
            )
            for lnk in db_note.outgoing_links
        ]
        return Note(
            id=db_note.id,
            title=db_note.title,
            content=db_note.content,
            note_type=NoteType(db_note.note_type),
            tags=tags,
            links=links,
            references=db_note.references,
            created_at=db_note.created_at,
            updated_at=db_note.updated_at,
        )

    def _convert_db_notes(self, db_notes: List[DBNote]) -> List[Note]:
        """Convert a list of DBNote objects to domain Notes, skipping conversion errors."""
        notes = []
        for db_note in db_notes:
            try:
                notes.append(self._db_note_to_note(db_note))
            except Exception as e:
                logger.error("Error converting note %s: %s", db_note.id, e)
        return notes

    def _get_or_create_tag(self, session: Session, tag_name: str) -> DBTag:
        """Return the DBTag with the given name, creating it if absent.

        Handles the TOCTOU race where two concurrent writers both see the tag
        as absent and attempt an INSERT: the loser catches IntegrityError,
        rolls back the savepoint, and re-queries to get the winner's row.
        """
        db_tag = session.scalar(select(DBTag).where(DBTag.name == tag_name))
        if not db_tag:
            db_tag = DBTag(name=tag_name)
            session.add(db_tag)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                db_tag = session.scalar(select(DBTag).where(DBTag.name == tag_name))
                if db_tag is None:
                    raise RuntimeError(
                        f"Failed to get or create tag '{tag_name}' after IntegrityError"
                    )
        return db_tag

    def _index_note(self, note: Note) -> None:
        """Index a note in the database."""
        with self.session_factory() as session:
            db_note = session.scalar(select(DBNote).where(DBNote.id == note.id))
            if db_note:
                db_note.title = note.title
                db_note.content = note.content
                db_note.note_type = note.note_type.value
                db_note.references = note.references
                db_note.updated_at = note.updated_at
                # Clear existing links and tags to rebuild them
                session.execute(delete(DBLink).where(DBLink.source_id == note.id))
                db_note.tags.clear()
            else:
                db_note = DBNote(
                    id=note.id,
                    title=note.title,
                    content=note.content,
                    note_type=note.note_type.value,
                    references_json=json.dumps(note.references),
                    created_at=note.created_at,
                    updated_at=note.updated_at
                )
                session.add(db_note)

            session.flush()  # Flush to get the note ID

            for tag in note.tags:
                db_note.tags.append(self._get_or_create_tag(session, tag.name))

            for link in note.links:
                existing_link = session.scalar(
                    select(DBLink).where(
                        (DBLink.source_id == link.source_id) &
                        (DBLink.target_id == link.target_id) &
                        (DBLink.link_type == link.link_type.value)
                    )
                )

                if not existing_link:
                    db_link = DBLink(
                        source_id=link.source_id,
                        target_id=link.target_id,
                        link_type=link.link_type.value,
                        description=link.description,
                        created_at=link.created_at
                    )
                    session.add(db_link)

            session.commit()

    def note_to_markdown(self, note: Note) -> str:
        """Convert a note to markdown with frontmatter."""
        metadata = {
            "id": note.id,
            "title": note.title,
            "type": note.note_type.value,
            "tags": [tag.name for tag in note.tags],
            "created": note.created_at.isoformat(),
            "updated": note.updated_at.isoformat()
        }
        if note.references:
            metadata["references"] = note.references
        metadata.update(note.metadata)

        # Avoid duplicate title heading.
        title_heading = f"# {note.title}"
        if note.content.strip().startswith(title_heading):
            content = note.content
        else:
            content = f"{title_heading}\n\n{note.content}"

        # Strip existing Links section before rewriting.
        content_parts = []
        skip_section = False
        for line in content.split("\n"):
            if line.strip() == "## Links":
                skip_section = True
                continue
            elif skip_section and line.startswith("## "):
                skip_section = False

            if not skip_section:
                content_parts.append(line)

        content = "\n".join(content_parts).rstrip()

        # Deduplicates links by target+type key.
        if note.links:
            unique_links = {}
            for link in note.links:
                key = f"{link.target_id}:{link.link_type.value}"
                unique_links[key] = link
            content += "\n\n## Links\n"
            for link in unique_links.values():
                desc = f" {link.description}" if link.description else ""
                content += f"- {link.link_type.value} [[{link.target_id}]]{desc}\n"

        post = frontmatter.Post(content, **metadata)
        return frontmatter.dumps(post)

    def create(self, note: Note) -> Note:
        """Create a new note."""
        if not note.id:
            from slipbox_mcp.models.schema import generate_id
            note.id = generate_id()

        markdown = self.note_to_markdown(note)

        file_path = self.notes_dir / f"{note.id}.md"
        try:
            with self.file_lock:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(markdown)
        except IOError as e:
            raise IOError(f"Failed to write note to {file_path}: {e}")

        try:
            self._index_note(note)
        except Exception:
            # Roll back file write to maintain consistency
            with self.file_lock:
                file_path.unlink(missing_ok=True)
            raise

        return note

    def get(self, id: str) -> Optional[Note]:
        """Get a note by ID."""
        file_path = self.notes_dir / f"{id}.md"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self._parse_note_from_markdown(content)
        except Exception as e:
            raise IOError(f"Failed to read note {id}: {e}")

    def get_by_title(self, title: str) -> Optional[Note]:
        """Get a note by title."""
        with self.session_factory() as session:
            db_note = session.scalar(
                select(DBNote).where(DBNote.title == title)
            )
            if not db_note:
                return None
            return self.get(db_note.id)

    def get_all(self) -> List[Note]:
        """Get all notes."""
        with self.session_factory() as session:
            query = select(DBNote).options(*_NOTE_EAGER_LOADS)
            result = session.execute(query)
            # unique() required to collapse duplicate rows from eager loading joins
            db_notes = result.unique().scalars().all()

            return self._convert_db_notes(db_notes)

    def update(self, note: Note) -> Note:
        """Update a note."""
        existing_note = self.get(note.id)
        if not existing_note:
            raise ValueError(f"Note with ID {note.id} does not exist")

        note.updated_at = datetime.datetime.now()

        markdown = self.note_to_markdown(note)

        file_path = self.notes_dir / f"{note.id}.md"
        try:
            with self.file_lock:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(markdown)
        except IOError as e:
            raise IOError(f"Failed to write note to {file_path}: {e}")

        try:
            with self.session_factory() as session:
                db_note = session.scalar(select(DBNote).where(DBNote.id == note.id))
                if db_note:
                    db_note.title = note.title
                    db_note.content = note.content
                    db_note.note_type = note.note_type.value
                    db_note.references = note.references
                    db_note.updated_at = note.updated_at

                    db_note.tags = []
                    for tag in note.tags:
                        db_note.tags.append(self._get_or_create_tag(session, tag.name))

                    # Delete-and-replace links rather than merging to avoid stale entries.
                    session.execute(delete(DBLink).where(DBLink.source_id == note.id))

                    for link in note.links:
                        db_link = DBLink(
                            source_id=link.source_id,
                            target_id=link.target_id,
                            link_type=link.link_type.value,
                            description=link.description,
                            created_at=link.created_at
                        )
                        session.add(db_link)

                    session.commit()
                else:
                    # File exists but DB row is missing — re-index to recover.
                    self._index_note(note)
        except Exception as e:
            logger.error("Failed to update note in database: %s", e)
            raise

        return note

    def delete(self, id: str) -> None:
        """Delete a note by ID."""
        file_path = self.notes_dir / f"{id}.md"
        if not file_path.exists():
            raise ValueError(f"Note with ID {id} does not exist")

        try:
            with self.file_lock:
                os.remove(file_path)
        except IOError as e:
            raise IOError(f"Failed to delete note {id}: {e}")

        # Cascade on DBNote handles outgoing_links and incoming_links;
        # the note_tags association table rows are removed via FK.
        with self.session_factory() as session:
            db_note = session.get(DBNote, id)
            if db_note:
                session.delete(db_note)
                session.commit()

    def search(self, **kwargs: Any) -> List[Note]:
        """Search for notes based on criteria."""
        with self.session_factory() as session:
            query = select(DBNote).options(*_NOTE_EAGER_LOADS)
            if "content" in kwargs:
                search_term = kwargs['content']
                # Search in both content and title since content might include the title
                query = query.where(
                    or_(
                        DBNote.content.like(f"%{search_term}%"),
                        DBNote.title.like(f"%{search_term}%")
                    )
                )
            if "title" in kwargs:
                search_title = kwargs['title']
                query = query.where(func.lower(DBNote.title).like(f"%{search_title.lower()}%"))
            if "note_type" in kwargs:
                note_type = (
                    kwargs["note_type"].value
                    if isinstance(kwargs["note_type"], NoteType)
                    else kwargs["note_type"]
                )
                query = query.where(DBNote.note_type == note_type)
            if "tag" in kwargs:
                tag_name = kwargs["tag"]
                query = query.join(DBNote.tags).where(DBTag.name == tag_name)
            if "tags" in kwargs:
                tag_names = kwargs["tags"]
                if isinstance(tag_names, list):
                    query = query.join(DBNote.tags).where(DBTag.name.in_(tag_names))
            if "linked_to" in kwargs:
                target_id = kwargs["linked_to"]
                query = query.join(DBNote.outgoing_links).where(DBLink.target_id == target_id)
            if "linked_from" in kwargs:
                source_id = kwargs["linked_from"]
                query = query.join(DBNote.incoming_links).where(DBLink.source_id == source_id)
            if "created_after" in kwargs:
                query = query.where(DBNote.created_at >= kwargs["created_after"])
            if "created_before" in kwargs:
                query = query.where(DBNote.created_at <= kwargs["created_before"])
            if "updated_after" in kwargs:
                query = query.where(DBNote.updated_at >= kwargs["updated_after"])
            if "updated_before" in kwargs:
                query = query.where(DBNote.updated_at <= kwargs["updated_before"])
            # Apply unique() to handle duplicates from joins
            result = session.execute(query)
            db_notes = result.unique().scalars().all()
        return self._convert_db_notes(db_notes)

    def find_by_tag(self, tag: Union[str, Tag]) -> List[Note]:
        """Find notes by tag."""
        tag_name = tag.name if isinstance(tag, Tag) else tag
        return self.search(tag=tag_name)

    def find_linked_notes(self, note_id: str, direction: str = "outgoing") -> List[Note]:
        """Find notes linked to/from this note."""
        with self.session_factory() as session:
            if direction == "outgoing":
                query = (
                    select(DBNote)
                    .join(DBLink, DBNote.id == DBLink.target_id)
                    .where(DBLink.source_id == note_id)
                    .options(*_NOTE_EAGER_LOADS)
                )
            elif direction == "incoming":
                query = (
                    select(DBNote)
                    .join(DBLink, DBNote.id == DBLink.source_id)
                    .where(DBLink.target_id == note_id)
                    .options(*_NOTE_EAGER_LOADS)
                )
            elif direction == "both":
                query = (
                    select(DBNote)
                    .join(
                        DBLink,
                        or_(
                            and_(DBNote.id == DBLink.target_id, DBLink.source_id == note_id),
                            and_(DBNote.id == DBLink.source_id, DBLink.target_id == note_id)
                        )
                    )
                    .options(*_NOTE_EAGER_LOADS)
                )
            else:
                raise ValueError(f"Invalid direction: {direction}. Use 'outgoing', 'incoming', or 'both'")

            result = session.execute(query)
            # unique() required to collapse duplicate rows from eager loading joins
            db_notes = result.unique().scalars().all()
            return self._convert_db_notes(db_notes)

    def get_all_tags(self) -> List[Tag]:
        """Get all tags in the system."""
        with self.session_factory() as session:
            result = session.execute(select(DBTag))
            db_tags = result.scalars().all()
        return [Tag(name=tag.name) for tag in db_tags]
