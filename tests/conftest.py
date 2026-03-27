"""Common test fixtures for the Zettelkasten MCP server."""
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from slipbox_mcp.config import config
from slipbox_mcp.models.db_models import Base
from slipbox_mcp.services.search_service import SearchService
from slipbox_mcp.services.zettel_service import ZettelService
from slipbox_mcp.storage.note_repository import NoteRepository


# ---------------------------------------------------------------------------
# Directory / config isolation
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_dirs():
    """Create temporary directories for notes and database."""
    with tempfile.TemporaryDirectory() as notes_dir:
        with tempfile.TemporaryDirectory() as db_dir:
            yield Path(notes_dir), Path(db_dir)


@pytest.fixture
def test_config(temp_dirs):
    """Configure with test paths, restoring originals after the test."""
    notes_dir, db_dir = temp_dirs
    database_path = db_dir / "test_zettelkasten.db"
    original_notes_dir = config.notes_dir
    original_database_path = config.database_path
    config.notes_dir = notes_dir
    config.database_path = database_path
    yield config
    config.notes_dir = original_notes_dir
    config.database_path = original_database_path


# ---------------------------------------------------------------------------
# Repository / service fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def note_repository(test_config):
    """Create an isolated NoteRepository backed by a fresh SQLite database."""
    database_path = test_config.get_absolute_path(test_config.database_path)
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    engine.dispose()
    repository = NoteRepository(notes_dir=test_config.notes_dir)
    yield repository


@pytest.fixture
def zettel_service(note_repository):
    """Create a ZettelService wired to the isolated test repository."""
    service = ZettelService(repository=note_repository)
    yield service


@pytest.fixture
def search_service(zettel_service):
    """Create a SearchService wired to the test ZettelService."""
    return SearchService(zettel_service)
