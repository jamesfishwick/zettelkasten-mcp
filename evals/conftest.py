"""Eval test configuration and helpers."""
import json
import os
import subprocess
from pathlib import Path

import pytest

from evals.seed_data import populate_slipbox

EVAL_MODEL = os.environ.get("EVAL_MODEL", "haiku")
EVALS_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Eval-specific fixtures (shared fixtures live in root conftest.py)
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
    max_budget_usd: float = 0.20,
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
