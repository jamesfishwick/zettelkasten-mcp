"""SQLAlchemy database models for the Zettelkasten MCP server."""
import datetime
from typing import List, Optional

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, Table,
                       Text, UniqueConstraint, create_engine)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from zettelkasten_mcp.config import config
from zettelkasten_mcp.models.schema import LinkType, NoteType

Base = declarative_base()

note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", String(255), ForeignKey("notes.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class DBNote(Base):
    """Database model for a note."""
    __tablename__ = "notes"
    id = Column(String(255), primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default=NoteType.PERMANENT.value, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    tags = relationship(
        "DBTag", secondary=note_tags, back_populates="notes"
    )
    outgoing_links = relationship(
        "DBLink",
        foreign_keys="DBLink.source_id",
        back_populates="source",
        cascade="all, delete-orphan"
    )
    incoming_links = relationship(
        "DBLink",
        foreign_keys="DBLink.target_id",
        back_populates="target",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Note(id='{self.id}', title='{self.title}')>"

class DBTag(Base):
    """Database model for a tag."""
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)

    notes = relationship(
        "DBNote", secondary=note_tags, back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}')>"

class DBLink(Base):
    """Database model for a link between notes."""
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(255), ForeignKey("notes.id"), nullable=False)
    target_id = Column(String(255), ForeignKey("notes.id"), nullable=False)
    link_type = Column(String(50), default=LinkType.REFERENCE.value, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    source = relationship(
        "DBNote", foreign_keys=[source_id], back_populates="outgoing_links"
    )
    target = relationship(
        "DBNote", foreign_keys=[target_id], back_populates="incoming_links"
    )

    # Add a unique constraint to prevent duplicate links of the same type
    __table_args__ = (
        UniqueConstraint('source_id', 'target_id', 'link_type',
                         name='unique_link_type'),
    )

    def __repr__(self) -> str:
        return (
            f"<Link(id={self.id}, source='{self.source_id}', "
            f"target='{self.target_id}', type='{self.link_type}')>"
        )

def init_db() -> None:
    """Initialize the database."""
    engine = create_engine(config.get_db_url())
    Base.metadata.create_all(engine)
    return engine

def get_session_factory(engine=None):
    """Get a session factory for the database."""
    if engine is None:
        engine = create_engine(config.get_db_url())
    return sessionmaker(bind=engine)
