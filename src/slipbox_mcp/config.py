"""Configuration module for the Zettelkasten MCP server."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()


def _expand_path(raw: str) -> Path:
    """Expand ~ in path strings and raise if expansion fails (e.g. ~nonexistentuser)."""
    expanded = os.path.expanduser(raw)
    if expanded.startswith("~"):
        raise ValueError(
            f"Path {raw!r} could not be expanded to an absolute path. "
            "Use a full absolute path instead of a tilde shortcut."
        )
    return Path(expanded)


class ZettelkastenConfig(BaseModel):
    """Configuration for the Zettelkasten server."""
    base_dir: Path = Field(
        default_factory=lambda: _expand_path(os.getenv("SLIPBOX_BASE_DIR", "."))
    )
    notes_dir: Path = Field(
        default_factory=lambda: _expand_path(os.getenv("SLIPBOX_NOTES_DIR", "data/notes"))
    )
    database_path: Path = Field(
        default_factory=lambda: _expand_path(
            os.getenv("SLIPBOX_DATABASE_PATH", "data/db/slipbox.db")
        )
    )
    server_name: str = Field(
        default=os.getenv("SLIPBOX_SERVER_NAME", "slipbox-mcp")
    )
    server_version: str = Field(default="1.2.1")
    id_date_format: str = Field(default="%Y%m%dT%H%M%S")
    default_note_template: str = Field(
        default=(
            "# {title}\n\n"
            "## Metadata\n"
            "- Created: {created_at}\n"
            "- Tags: {tags}\n\n"
            "## Content\n\n"
            "{content}\n\n"
            "## Links\n"
            "{links}\n"
        )
    )

    def get_absolute_path(self, path: Path) -> Path:
        """Convert a relative path to an absolute path based on base_dir."""
        if path.is_absolute():
            return path
        return self.base_dir / path

    def get_db_url(self) -> str:
        """Get the database URL for SQLite."""
        db_path = self.get_absolute_path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"

try:
    config = ZettelkastenConfig()
except (ValueError, ValidationError) as e:
    print(f"Configuration error: {e}", file=sys.stderr)
    raise SystemExit(1) from e
