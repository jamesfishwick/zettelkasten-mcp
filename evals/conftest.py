"""Eval test configuration and helpers."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from slipbox_mcp.config import config
from slipbox_mcp.models.db_models import Base
from slipbox_mcp.services.zettel_service import ZettelService
from slipbox_mcp.storage.note_repository import NoteRepository

from evals.seed_data import populate_slipbox

EVAL_MODEL = os.environ.get("EVAL_MODEL", "haiku")
EVALS_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Base fixtures (mirrored from tests/conftest.py for eval isolation)
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


# ---------------------------------------------------------------------------
# Eval-specific fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_slipbox(zettel_service):
    """A zettel_service pre-populated with realistic seed data."""
    refs = populate_slipbox(zettel_service)
    return zettel_service, refs


def run_claude_eval(
    prompt: str,
    notes_dir: Path,
    db_path: Path,
    model: str = EVAL_MODEL,
    max_budget_usd: float = 0.50,
) -> dict:
    """Run claude CLI with MCP server pointing at test slipbox.

    Returns dict with 'output', 'exit_code', 'cost_usd', and 'stderr'.
    """
    # Use the venv's python so the MCP server subprocess can find slipbox_mcp
    import sys
    python_path = sys.executable

    mcp_config = {
        "mcpServers": {
            "slipbox": {
                "command": python_path,
                "args": ["-c", "from slipbox_mcp.main import main; main()"],
                "env": {
                    "SLIPBOX_NOTES_DIR": str(notes_dir),
                    "SLIPBOX_DATABASE_PATH": str(db_path),
                },
            }
        }
    }
    mcp_config_json = json.dumps(mcp_config)

    result = subprocess.run(
        [
            "claude", "-p", prompt,
            "--model", model,
            "--output-format", "json",
            "--max-budget-usd", str(max_budget_usd),
            "--mcp-config", mcp_config_json,
            "--strict-mcp-config",
            "--dangerously-skip-permissions",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = ""
    cost = 0.0
    raw_data = {}
    try:
        raw_data = json.loads(result.stdout)
        output = raw_data.get("result", result.stdout)
        cost = raw_data.get("total_cost_usd", 0.0)
    except (json.JSONDecodeError, KeyError):
        output = result.stdout

    return {
        "output": output,
        "exit_code": result.returncode,
        "cost_usd": cost,
        "stderr": result.stderr,
        "raw": raw_data,
    }
