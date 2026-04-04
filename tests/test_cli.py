"""Tests for CLI --base-dir flag and config warnings."""
import subprocess
import sys


def _run_cli(*args, env=None):
    """Run the slipbox CLI and return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "slipbox_mcp.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_help_shows_base_dir():
    """--help output should mention the --base-dir flag."""
    result = _run_cli("--help")
    assert "--base-dir" in result.stdout


def test_warns_on_default_base_dir():
    """Running with no --base-dir and no SLIPBOX_BASE_DIR should warn on stderr."""
    import os

    env = os.environ.copy()
    env.pop("SLIPBOX_BASE_DIR", None)
    result = _run_cli("status", env=env)
    assert "Warning: No --base-dir or SLIPBOX_BASE_DIR set" in result.stderr


def test_base_dir_flag_accepted():
    """--base-dir /tmp should be accepted without error."""
    result = _run_cli("--base-dir", "/tmp", "status")
    assert result.returncode == 0
