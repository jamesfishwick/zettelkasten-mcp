"""Utility functions for the Zettelkasten MCP server."""
import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Set up logging configuration."""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    log_config = {
        "level": numeric_level,
        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S",
    }

    if log_file:
        log_config["filename"] = log_file
        log_config["filemode"] = "a"
    else:
        log_config["stream"] = sys.stderr

    logging.basicConfig(**log_config)

def parse_tags(tags_str: str) -> list[str]:
    """Parse a comma-separated list of tags into a list of tag strings."""
    if not tags_str:
        return []
    return [tag.strip() for tag in tags_str.split(",") if tag.strip()]

def format_note_for_display(title: str, id: str, content: str, tags: list[str],
                          created_at: datetime, updated_at: datetime,
                          links: Optional[list] = None) -> str:
    """Format a note for display in the console."""
    result = f"# {title}\n"
    result += f"ID: {id}\n"
    result += f"Created: {created_at.isoformat()}\n"
    result += f"Updated: {updated_at.isoformat()}\n"

    if tags:
        result += f"Tags: {', '.join(tags)}\n"

    result += f"\n{content}\n"

    if links:
        result += "\n## Links\n"
        for link in links:
            if hasattr(link, "description") and link.description:
                result += f"- {link.link_type.value}: {link.target_id} - {link.description}\n"
            else:
                result += f"- {link.link_type.value}: {link.target_id}\n"

    return result
