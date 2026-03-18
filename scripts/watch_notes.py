#!/usr/bin/env python3
"""
Background daemon that watches the notes directory and rebuilds the index on changes.
Runs as a separate process from the MCP server for persistent monitoring.

Usage:
    python scripts/watch_notes.py

The watcher triggers a database rebuild when markdown files are created, modified,
or deleted. It debounces rapid changes to avoid excessive rebuilds during editing.
"""
import sys
import time
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from slipbox_mcp.config import config
from slipbox_mcp.storage.note_repository import NoteRepository


class NotesChangeHandler(FileSystemEventHandler):
    """Handles file system events in the notes directory."""

    def __init__(self, debounce_seconds: float = 2.0):
        super().__init__()
        self.debounce_seconds = debounce_seconds
        self.last_rebuild = 0.0
        self.logger = logging.getLogger(__name__)

    def should_rebuild(self, event) -> bool:
        """Check if we should trigger a rebuild for this event."""
        # Ignore directory events
        if event.is_directory:
            return False

        # Only rebuild for markdown files
        src_path = getattr(event, 'src_path', '') or ''
        if not src_path.endswith('.md'):
            return False

        # Debounce: don't rebuild more than once per N seconds
        now = time.time()
        if now - self.last_rebuild < self.debounce_seconds:
            self.logger.debug(f"Debounced rebuild (last was {now - self.last_rebuild:.1f}s ago)")
            return False

        return True

    def trigger_rebuild(self, reason: str = "file change"):
        """Rebuild the index."""
        try:
            self.logger.info(f"Notes changed ({reason}), rebuilding index...")
            repo = NoteRepository()
            repo.rebuild_index()
            self.last_rebuild = time.time()
            self.logger.info("Index rebuild complete")
        except Exception as e:
            self.logger.error(f"Failed to rebuild index: {e}")

    def on_modified(self, event):
        if self.should_rebuild(event):
            self.trigger_rebuild(f"modified: {Path(event.src_path).name}")

    def on_created(self, event):
        if self.should_rebuild(event):
            self.trigger_rebuild(f"created: {Path(event.src_path).name}")

    def on_deleted(self, event):
        if self.should_rebuild(event):
            self.trigger_rebuild(f"deleted: {Path(event.src_path).name}")

    def on_moved(self, event):
        # Handle renames
        if self.should_rebuild(event):
            self.trigger_rebuild(f"moved: {Path(event.src_path).name}")


def setup_logging(level: str = "INFO"):
    """Configure logging for the watcher."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Run the file watcher daemon."""
    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    notes_dir = config.get_absolute_path(config.notes_dir)

    if not notes_dir.exists():
        logger.error(f"Notes directory does not exist: {notes_dir}")
        sys.exit(1)

    logger.info(f"Starting file watcher for: {notes_dir}")
    logger.info("Press Ctrl+C to stop")

    event_handler = NotesChangeHandler(debounce_seconds=2.0)
    observer = Observer()
    observer.schedule(event_handler, str(notes_dir), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping file watcher...")
        observer.stop()

    observer.join()
    logger.info("File watcher stopped")


if __name__ == "__main__":
    main()
