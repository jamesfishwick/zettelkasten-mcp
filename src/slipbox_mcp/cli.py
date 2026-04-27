#!/usr/bin/env python3
"""Slipbox CLI for maintenance and inspection tasks.

This CLI provides mechanical/read-only operations that don't require agent
intelligence. It complements the MCP server (which handles intelligent note
creation and linking via the MCP server) with quick terminal access.

Philosophy: The CLI handles *what exists*. The agent handles *what should exist*.
"""
import argparse
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

# Handle broken pipe gracefully (e.g., when piping to head)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

import frontmatter  # noqa: E402

from slipbox_mcp.formatting import format_cluster_summary, format_note_compact  # noqa: E402
from slipbox_mcp.services.zettel_service import ZettelService  # noqa: E402
from slipbox_mcp.services.cluster_service import ClusterService  # noqa: E402
from slipbox_mcp.services.search_service import SearchService  # noqa: E402
from slipbox_mcp.storage.note_repository import NoteRepository  # noqa: E402


def cmd_status(args):
    """Show Zettelkasten status."""
    try:
        zettel = ZettelService()
        cluster = ClusterService(zettel)

        notes = zettel.get_all_notes()
        tags = zettel.get_all_tags()
        report = cluster.load_report()

        # Count orphans via SQL (replaces O(n^2) in-memory loop)
        search = SearchService(zettel)
        orphan_count = len(search.find_orphaned_notes())

        print(f"Notes: {len(notes)}")
        print(f"Tags: {len(tags)}")
        print(f"Orphans: {orphan_count}")

        if report:
            active = [c for c in report.clusters if c.id not in report.dismissed_cluster_ids]
            age = (datetime.now() - report.generated_at).total_seconds() / 3600
            print(f"Pending clusters: {len(active)}")
            print(f"Report age: {age:.1f}h")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_search(args):
    """Search notes."""
    try:
        zettel = ZettelService()
        search = SearchService(zettel)
        results = search.search_by_text(args.query)

        if not results:
            print("No results found.")
            return

        for result in results[:args.limit]:
            print(format_note_compact(result.note))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_clusters(args):
    """Show clusters needing structure notes."""
    try:
        zettel = ZettelService()
        cluster = ClusterService(zettel)
        report = cluster.load_report()

        if not report:
            print("No cluster report. Run: slipbox rebuild --clusters")
            return

        active = [c for c in report.clusters if c.id not in report.dismissed_cluster_ids]

        if not active:
            print("No pending clusters.")
            return

        for c in active[:args.limit]:
            print(format_cluster_summary(c))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_orphans(args):
    """List orphaned notes."""
    try:
        zettel = ZettelService()
        search = SearchService(zettel)
        orphans = search.find_orphaned_notes()

        if not orphans:
            print("No orphaned notes.")
            return

        print(f"Found {len(orphans)} orphaned notes:\n")
        for note in orphans[:args.limit]:
            print(format_note_compact(note))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_rebuild(args):
    """Rebuild the index."""
    try:
        repo = NoteRepository()
        print("Rebuilding index...")
        repo.rebuild_index()
        print("Index rebuilt.")

        if args.clusters:
            print("Refreshing clusters...")
            zettel = ZettelService()
            cluster = ClusterService(zettel)
            report = cluster.detect_clusters()
            cluster.save_report(report)
            print(f"Found {report.stats['clusters_needing_structure']} clusters.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_export(args):
    """Export a note to stdout."""
    try:
        zettel = ZettelService()
        note = zettel.get_note(args.note_id)

        if not note:
            print(f"Note not found: {args.note_id}", file=sys.stderr)
            sys.exit(1)

        try:
            print(zettel.export_note(note.id))
        except ValueError as e:
            print(f"Export failed: {e}", file=sys.stderr)
            sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _scan_literature_notes_missing_refs(notes_dir: Path) -> list[tuple[Path, dict]]:
    """Return (path, metadata) for every literature note with no references.

    Reads frontmatter directly without constructing Pydantic Note objects, so
    this scan is safe to run even when the literature/references validator
    would reject the very notes we are trying to surface.
    """
    offenders: list[tuple[Path, dict]] = []
    for file_path in sorted(notes_dir.glob("*.md")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
        except Exception as e:
            print(f"Warning: could not parse {file_path.name}: {e}", file=sys.stderr)
            continue

        if post.metadata.get("type") != "literature":
            continue

        refs = post.metadata.get("references")
        if isinstance(refs, list):
            has_refs = any(str(r).strip() for r in refs)
        elif isinstance(refs, str):
            has_refs = bool(refs.strip())
        else:
            has_refs = False

        if not has_refs:
            offenders.append((file_path, post.metadata))
    return offenders


def cmd_audit_references(args):
    """Audit literature notes for missing references.

    Without --fix, lists offenders. With --fix downgrade, rewrites their
    frontmatter type to 'permanent' and re-indexes the database.
    """
    try:
        from slipbox_mcp.config import config as _config
        notes_dir = _config.get_absolute_path(_config.notes_dir)

        offenders = _scan_literature_notes_missing_refs(notes_dir)

        if not offenders:
            print("All literature notes have references.")
            return

        print(f"Found {len(offenders)} literature note(s) without references:\n")
        for path, metadata in offenders:
            note_id = metadata.get("id", path.stem)
            title = metadata.get("title", "(untitled)")
            created = metadata.get("created", "?")
            print(f"  {note_id}  {title}")
            print(f"    Created: {created}")
            print(f"    Path:    {path}")
            print()

        if args.fix != "downgrade":
            print("Run with --fix downgrade to convert these to 'permanent' notes.")
            print("Or add references manually and re-run.")
            return

        print(f"Downgrading {len(offenders)} note(s) to type='permanent'...")
        for path, _metadata in offenders:
            with open(path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
            post.metadata["type"] = "permanent"
            with open(path, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))
            print(f"  downgraded {path.name}")

        print("\nRe-indexing database...")
        repo = NoteRepository()
        repo.rebuild_index()
        print("Done.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_tags(args):
    """List all tags."""
    try:
        zettel = ZettelService()
        notes = zettel.get_all_notes()

        # Count notes per tag
        tag_counts = {}
        for note in notes:
            for tag in note.tags:
                tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1

        sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])

        for name, count in sorted_tags:
            print(f"{count:4d}  {name}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="slipbox",
        description="Zettelkasten CLI for maintenance and inspection"
    )
    parser.add_argument("--base-dir", type=str, help="Path to slipbox data directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Show Zettelkasten status")

    # search
    p_search = subparsers.add_parser("search", help="Search notes")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-n", "--limit", type=int, default=10, help="Max results")

    # clusters
    p_clusters = subparsers.add_parser("clusters", help="Show pending clusters")
    p_clusters.add_argument("-n", "--limit", type=int, default=5, help="Max clusters")

    # orphans
    p_orphans = subparsers.add_parser("orphans", help="List orphaned notes")
    p_orphans.add_argument("-n", "--limit", type=int, default=20, help="Max results")

    # rebuild
    p_rebuild = subparsers.add_parser("rebuild", help="Rebuild index")
    p_rebuild.add_argument("--clusters", action="store_true", help="Also refresh clusters")

    # export
    p_export = subparsers.add_parser("export", help="Export note to stdout")
    p_export.add_argument("note_id", help="Note ID or title")

    # tags
    subparsers.add_parser("tags", help="List all tags with counts")

    # audit-references
    p_audit = subparsers.add_parser(
        "audit-references",
        help="List literature notes missing references"
    )
    p_audit.add_argument(
        "--fix",
        choices=["downgrade"],
        default=None,
        help="Apply a fix: 'downgrade' converts offenders to type=permanent",
    )

    args = parser.parse_args()

    from slipbox_mcp.config import config

    if args.base_dir:
        config.base_dir = Path(args.base_dir)
    elif config.base_dir == Path(".") and not os.getenv("SLIPBOX_BASE_DIR"):
        print(
            "Warning: No --base-dir or SLIPBOX_BASE_DIR set. Using current directory.",
            file=sys.stderr,
        )

    commands = {
        "status": cmd_status,
        "search": cmd_search,
        "clusters": cmd_clusters,
        "orphans": cmd_orphans,
        "rebuild": cmd_rebuild,
        "export": cmd_export,
        "tags": cmd_tags,
        "audit-references": cmd_audit_references,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
