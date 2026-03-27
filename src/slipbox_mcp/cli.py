#!/usr/bin/env python3
"""Zettelkasten CLI for maintenance and inspection tasks.

This CLI provides mechanical/read-only operations that don't require agent
intelligence. It complements the MCP server (which handles intelligent note
creation and linking via Claude) with quick terminal access.

Philosophy: The CLI handles *what exists*. The agent handles *what should exist*.
"""
import argparse
import signal
import sys
from datetime import datetime

# Handle broken pipe gracefully (e.g., when piping to head)
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

from slipbox_mcp.services.zettel_service import ZettelService
from slipbox_mcp.services.cluster_service import ClusterService
from slipbox_mcp.services.search_service import SearchService
from slipbox_mcp.storage.note_repository import NoteRepository


def cmd_status(args):
    """Show Zettelkasten status."""
    zettel = ZettelService()
    cluster = ClusterService(zettel)

    notes = zettel.get_all_notes()
    tags = zettel.get_all_tags()
    report = cluster.load_report()

    # Count orphans
    orphan_count = sum(
        1 for n in notes
        if not n.links and not any(
            link.target_id == n.id
            for other in notes
            for link in other.links
        )
    )

    print(f"Notes: {len(notes)}")
    print(f"Tags: {len(tags)}")
    print(f"Orphans: {orphan_count}")

    if report:
        active = [c for c in report.clusters if c.id not in report.dismissed_cluster_ids]
        age = (datetime.now() - report.generated_at).total_seconds() / 3600
        print(f"Pending clusters: {len(active)}")
        print(f"Report age: {age:.1f}h")


def cmd_search(args):
    """Search notes."""
    zettel = ZettelService()
    search = SearchService(zettel)
    results = search.search_by_text(args.query)

    if not results:
        print("No results found.")
        return

    for result in results[:args.limit]:
        note = result.note
        tags = ", ".join(t.name for t in note.tags[:3])
        print(f"{note.id[:12]}  {note.title}")
        if tags:
            print(f"            [{tags}]")


def cmd_clusters(args):
    """Show clusters needing structure notes."""
    zettel = ZettelService()
    cluster = ClusterService(zettel)
    report = cluster.load_report()

    if not report:
        print("No cluster report. Run: zk rebuild --clusters")
        return

    active = [c for c in report.clusters if c.id not in report.dismissed_cluster_ids]

    if not active:
        print("No pending clusters.")
        return

    for c in active[:args.limit]:
        print(f"\n{c.suggested_title}")
        print(f"  Score: {c.score:.2f} | Notes: {c.note_count} | Orphans: {c.orphan_count}")
        print(f"  Tags: {', '.join(c.tags[:5])}")
        print(f"  ID: {c.id}")


def cmd_orphans(args):
    """List orphaned notes."""
    zettel = ZettelService()
    notes = zettel.get_all_notes()

    orphans = []

    for note in notes:
        has_incoming = any(
            link.target_id == note.id
            for other in notes
            for link in other.links
        )
        if not note.links and not has_incoming:
            orphans.append(note)

    if not orphans:
        print("No orphaned notes.")
        return

    print(f"Found {len(orphans)} orphaned notes:\n")
    for note in orphans[:args.limit]:
        print(f"{note.id[:12]}  {note.title}")


def cmd_rebuild(args):
    """Rebuild the index."""
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


def cmd_export(args):
    """Export a note to stdout."""
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


def cmd_tags(args):
    """List all tags."""
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


def main():
    parser = argparse.ArgumentParser(
        prog="zk",
        description="Zettelkasten CLI for maintenance and inspection"
    )
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

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "search": cmd_search,
        "clusters": cmd_clusters,
        "orphans": cmd_orphans,
        "rebuild": cmd_rebuild,
        "export": cmd_export,
        "tags": cmd_tags,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
