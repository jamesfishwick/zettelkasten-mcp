"""Utility functions for the Zettelkasten MCP server."""
import logging
import sys
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

def parse_tags(tags_str: Optional[str]) -> list[str]:
    """Parse a comma-separated list of tags into a list of tag strings."""
    if not tags_str:
        return []
    return [tag.strip() for tag in tags_str.split(",") if tag.strip()]


def parse_refs(references: Optional[str]) -> list[str]:
    """Parse a newline-separated references string into a list of stripped entries."""
    if not references:
        return []
    return [r.strip() for r in references.split("\n") if r.strip()]


def content_preview(text: str, max_length: int = 100) -> str:
    """Return a single-line preview of *text*, truncated with ellipsis if needed."""
    preview = text[:max_length].replace("\n", " ")
    if len(text) > max_length:
        preview += "..."
    return preview


def format_tags(tags: list) -> str:
    """Format a list of Tag objects as a comma-separated string."""
    return ", ".join(tag.name for tag in tags)

