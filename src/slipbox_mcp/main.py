#!/usr/bin/env python
"""Main entry point for the Zettelkasten MCP server."""
import argparse
import logging
import os
import sys
from pathlib import Path

from slipbox_mcp.config import config
from slipbox_mcp.models.db_models import init_db
from slipbox_mcp.server.mcp_server import ZettelkastenMcpServer
from slipbox_mcp.utils import setup_logging

_RENAMED_ENV_VARS = {
    "ZETTELKASTEN_NOTES_DIR": "SLIPBOX_NOTES_DIR",
    "ZETTELKASTEN_DATABASE_PATH": "SLIPBOX_DATABASE_PATH",
    "ZETTELKASTEN_LOG_LEVEL": "SLIPBOX_LOG_LEVEL",
    "ZETTELKASTEN_BASE_DIR": "SLIPBOX_BASE_DIR",
    "ZETTELKASTEN_SERVER_NAME": "SLIPBOX_SERVER_NAME",
}


def _warn_renamed_env_vars() -> None:
    """Warn if any old ZETTELKASTEN_* env vars are set but no longer read."""
    _logger = logging.getLogger(__name__)
    for old, new in _RENAMED_ENV_VARS.items():
        if os.environ.get(old):
            _logger.warning(
                "Env var %s is set but no longer read. Rename it to %s. "
                "Your configuration is NOT being applied.",
                old, new,
            )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Zettelkasten MCP Server")
    parser.add_argument(
        "--notes-dir",
        help="Directory for storing note files",
        type=str,
        default=os.environ.get("SLIPBOX_NOTES_DIR")
    )
    parser.add_argument(
        "--database-path",
        help="SQLite database file path",
        type=str,
        default=os.environ.get("SLIPBOX_DATABASE_PATH")
    )
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.environ.get("SLIPBOX_LOG_LEVEL", "INFO")
    )
    return parser.parse_args()

def update_config(args):
    """Update the global config with command line arguments."""
    if args.notes_dir:
        config.notes_dir = Path(args.notes_dir)
    if args.database_path:
        config.database_path = Path(args.database_path)

def main():
    """Run the Zettelkasten MCP server."""
    args = parse_args()
    update_config(args)

    setup_logging(args.log_level)
    _warn_renamed_env_vars()
    logger = logging.getLogger(__name__)

    notes_dir = config.get_absolute_path(config.notes_dir)
    notes_dir.mkdir(parents=True, exist_ok=True)
    db_dir = config.get_absolute_path(config.database_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Using SQLite database: {config.get_db_url()}")
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    try:
        logger.info("Starting Zettelkasten MCP server")
        server = ZettelkastenMcpServer()
        server.run()
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
