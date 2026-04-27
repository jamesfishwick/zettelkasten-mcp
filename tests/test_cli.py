"""Tests for CLI --base-dir flag and config warnings."""
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


def _run_cli(*args, env=None):
    """Run the slipbox CLI and return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, "-m", "slipbox_mcp.cli", *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _write_note(notes_dir: Path, note_id: str, note_type: str,
                refs: list[str] | None = None) -> Path:
    """Write a minimal markdown note with the given frontmatter.

    Built without textwrap.dedent because dedent's common-prefix logic
    breaks when interpolated multi-line strings (refs block) lack the
    template's indentation, producing malformed YAML for refs paths.
    """
    lines = [
        "---",
        f"id: {note_id}",
        f"title: Test {note_id}",
        f"type: {note_type}",
        "created: '2026-01-01T00:00:00.000000'",
        "updated: '2026-01-01T00:00:00.000000'",
    ]
    if refs:
        lines.append("references:")
        for r in refs:
            lines.append(f"- {r}")
    lines.extend(["---", "", f"# Test {note_id}", "", "Some content.", ""])
    path = notes_dir / f"{note_id}.md"
    path.write_text("\n".join(lines))
    return path


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


def test_orphans_command_runs():
    """slipbox orphans should exit 0."""
    result = _run_cli("--base-dir", "/tmp", "orphans")
    assert result.returncode == 0


def test_status_shows_orphan_count():
    """slipbox status output should contain 'Orphans:'."""
    result = _run_cli("--base-dir", "/tmp", "status")
    assert result.returncode == 0
    assert "Orphans:" in result.stdout


def test_status_handles_error_gracefully():
    """Service errors should produce clean 'Error:' messages, not tracebacks."""
    import os

    env = os.environ.copy()
    env["SLIPBOX_BASE_DIR"] = "/nonexistent/readonly/path"
    result = _run_cli("status", env=env)
    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_search_handles_error_gracefully():
    """Search against a broken path should produce clean error output."""
    import os

    env = os.environ.copy()
    env["SLIPBOX_BASE_DIR"] = "/nonexistent/readonly/path"
    result = _run_cli("search", "test-query", env=env)
    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_rebuild_handles_error_gracefully():
    """Rebuild against a broken path should produce clean error output."""
    import os

    env = os.environ.copy()
    env["SLIPBOX_BASE_DIR"] = "/nonexistent/readonly/path"
    result = _run_cli("rebuild", env=env)
    assert result.returncode == 1
    assert "Error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_audit_references_clean_slipbox():
    """When all literature notes have references, audit reports nothing to fix."""
    with tempfile.TemporaryDirectory() as base:
        base_path = Path(base)
        notes_dir = base_path / "data" / "notes"
        notes_dir.mkdir(parents=True)
        _write_note(notes_dir, "20260101T000000000000001", "literature",
                    refs=["https://example.com/source"])
        _write_note(notes_dir, "20260101T000000000000002", "permanent")

        result = _run_cli("--base-dir", str(base_path), "audit-references")
        assert result.returncode == 0, result.stderr
        assert "All literature notes have references" in result.stdout


def test_audit_references_lists_offenders():
    """Literature notes without references are listed; --fix not yet applied."""
    with tempfile.TemporaryDirectory() as base:
        base_path = Path(base)
        notes_dir = base_path / "data" / "notes"
        notes_dir.mkdir(parents=True)
        _write_note(notes_dir, "20260101T000000000000003", "literature")
        _write_note(notes_dir, "20260101T000000000000004", "permanent")

        result = _run_cli("--base-dir", str(base_path), "audit-references")
        assert result.returncode == 0, result.stderr
        assert "Found 1 literature note(s) without references" in result.stdout
        assert "20260101T000000000000003" in result.stdout
        # Permanent note must not be listed
        assert "20260101T000000000000004" not in result.stdout
        # File should be unchanged (no fix applied)
        path = notes_dir / "20260101T000000000000003.md"
        assert "type: literature" in path.read_text()


def test_audit_references_fix_downgrade():
    """--fix downgrade rewrites offenders to type=permanent."""
    with tempfile.TemporaryDirectory() as base:
        base_path = Path(base)
        notes_dir = base_path / "data" / "notes"
        notes_dir.mkdir(parents=True)
        _write_note(notes_dir, "20260101T000000000000005", "literature")
        _write_note(notes_dir, "20260101T000000000000006", "literature",
                    refs=["https://example.com/source"])

        result = _run_cli(
            "--base-dir", str(base_path),
            "audit-references", "--fix", "downgrade",
        )
        assert result.returncode == 0, result.stderr

        offender = (notes_dir / "20260101T000000000000005.md").read_text()
        assert "type: permanent" in offender
        assert "type: literature" not in offender

        # Note that already had refs is untouched.
        ok = (notes_dir / "20260101T000000000000006.md").read_text()
        assert "type: literature" in ok


def test_audit_references_fix_preserves_frontmatter_key_order():
    """--fix downgrade must rewrite ONLY the type: line, leaving every other
    line byte-identical. Guards against cosmetic git-diff churn from
    re-serializing the entire frontmatter dict."""
    with tempfile.TemporaryDirectory() as base:
        base_path = Path(base)
        notes_dir = base_path / "data" / "notes"
        notes_dir.mkdir(parents=True)
        # Hand-author a note with non-alphabetical key order and a custom
        # field that frontmatter.dumps would round-trip differently.
        path = notes_dir / "20260101T000000000000020.md"
        original = (
            "---\n"
            "title: Order Preservation Test\n"
            "type: literature\n"
            "id: 20260101T000000000000020\n"
            "tags:\n"
            "- ordering\n"
            "- preservation\n"
            "created: '2026-01-01T00:00:00.000000'\n"
            "updated: '2026-01-01T00:00:00.000000'\n"
            "custom_field: keep-me-here\n"
            "---\n"
            "\n"
            "# Body content\n"
            "\n"
            "Some text.\n"
        )
        path.write_text(original)

        result = _run_cli(
            "--base-dir", str(base_path),
            "audit-references", "--fix", "downgrade",
        )
        assert result.returncode == 0, result.stderr

        rewritten = path.read_text()
        # Only the type: literature line should change.
        expected = original.replace("type: literature", "type: permanent")
        assert rewritten == expected, (
            f"Frontmatter rewrite changed bytes outside the 'type:' line.\n"
            f"--- expected ---\n{expected}\n"
            f"--- got ---\n{rewritten}"
        )


def test_audit_references_surfaces_malformed_yaml_on_stdout():
    """Malformed frontmatter must NOT be silently classified as 'not literature'.
    Audit reports unparseable files in stdout (not just stderr) and exits 1.
    """
    with tempfile.TemporaryDirectory() as base:
        base_path = Path(base)
        notes_dir = base_path / "data" / "notes"
        notes_dir.mkdir(parents=True)
        # Valid offender so the test exercises both branches
        _write_note(notes_dir, "20260101T000000000000010", "literature")
        # Malformed frontmatter: unterminated key value, will fail YAML parse
        broken = notes_dir / "20260101T000000000000011.md"
        broken.write_text("---\nid: 20260101T000000000000011\ntitle: \"unterminated\n---\n\nbody\n")

        result = _run_cli("--base-dir", str(base_path), "audit-references")
        # Unparseable file present → non-zero exit even without --fix
        assert result.returncode == 1, result.stderr
        assert "Could not audit 1 file(s)" in result.stdout, (
            f"Unparseable file must be surfaced on stdout, not just stderr. "
            f"stdout={result.stdout!r}"
        )
        assert "20260101T000000000000011.md" in result.stdout
        assert "20260101T000000000000010" in result.stdout, (
            "Valid offender should still be listed alongside unparseable files."
        )


def test_audit_references_fix_makes_subsequent_runs_clean():
    """After --fix downgrade, a follow-up audit reports a clean slipbox."""
    with tempfile.TemporaryDirectory() as base:
        base_path = Path(base)
        notes_dir = base_path / "data" / "notes"
        notes_dir.mkdir(parents=True)
        _write_note(notes_dir, "20260101T000000000000007", "literature")

        fix_result = _run_cli(
            "--base-dir", str(base_path),
            "audit-references", "--fix", "downgrade",
        )
        assert fix_result.returncode == 0, fix_result.stderr

        rerun = _run_cli("--base-dir", str(base_path), "audit-references")
        assert rerun.returncode == 0, rerun.stderr
        assert "All literature notes have references" in rerun.stdout
