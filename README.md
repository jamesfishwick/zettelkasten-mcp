# Zettelkasten MCP Server

Model Context Protocol server for managing a Zettelkasten knowledge system with automatic cluster detection.

## Features

- **Atomic Notes**: Create, update, and link notes following Zettelkasten principles
- **Semantic Links**: Seven link types (reference, extends, refines, contradicts, questions, supports, related)
- **Full-Text Search**: Search across titles, content, and tags
- **Graph Analysis**: Find central notes, orphans, and similar notes
- **Cluster Detection**: Identifies emergent knowledge clusters
- **Structure Note Generation**: Create structure notes from detected clusters

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/zettelkasten-mcp.git
cd zettelkasten-mcp

pipx install --editable .
```

### 2. Configure Environment

Create a `.env` file or set environment variables:

```bash
# Where notes are stored as markdown files
export ZETTELKASTEN_NOTES_DIR="~/.local/share/mcp/zettelkasten/notes"

# SQLite database path
export ZETTELKASTEN_DATABASE_PATH="~/.local/share/mcp/zettelkasten/data/zettelkasten.db"

# Optional: Log level (DEBUG, INFO, WARNING, ERROR)
export ZETTELKASTEN_LOG_LEVEL="INFO"
```

Or copy the example:

```bash
cp .env.example .env
# Edit .env with your paths
```

### 3. Initialize Data Directories

```bash
mkdir -p ~/.local/share/mcp/zettelkasten/notes
mkdir -p ~/.local/share/mcp/zettelkasten/data
```

The server creates these automatically, but explicit creation helps verify permissions.

### 4. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "zettelkasten": {
      "command": "/absolute/path/to/zettelkasten-mcp/.venv/bin/python",
      "args": ["-m", "zettelkasten_mcp.main"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/zettelkasten-mcp/src",
        "ZETTELKASTEN_NOTES_DIR": "~/.local/share/mcp/zettelkasten/notes",
        "ZETTELKASTEN_DATABASE_PATH": "~/.local/share/mcp/zettelkasten/data/zettelkasten.db"
      }
    }
  }
}
```

Replace `/absolute/path/to/` with your actual path. The `PYTHONPATH` must point to the `src/` directory so Python can find the package without installing it into the venv.

### 5. Restart Claude Desktop

Quit and reopen Claude Desktop to load the MCP server.

### 6. Verify Installation

In Claude:

- "Create a test note about something"
- "Search my zettelkasten for test"
- "Find orphaned notes"

---

## Optional: Automatic Cluster Detection

Cluster analysis scans all notes and computes similarity scores. Running it daily (6am) pre-computes results so `zk_get_cluster_report()` returns instantly. Without scheduling, cluster detection runs on-demand, which is slower for large collections.

Run manually after bulk imports, major reorganization, or when you want immediate results.

### Install (macOS)

```bash
chmod +x scripts/install-cluster-detection.sh
./scripts/install-cluster-detection.sh
```

The installer detects your Python/venv path, generates the LaunchAgent plist, and loads it.

### Manual Test (File Watcher)

```bash
source .venv/bin/activate
python scripts/detect_clusters.py
```

Output saved to `~/.local/share/mcp/zettelkasten/cluster-analysis.json`.

### Uninstall

```bash
./scripts/install-cluster-detection.sh --uninstall
```

---

## Optional: File Watcher for Auto-Indexing

The MCP server maintains a database index for fast searching. Editing notes in Obsidian (or any editor) makes the database stale until you run `zk_rebuild_index`.

The file watcher runs as a background daemon, monitoring your notes directory and automatically rebuilding the index when `.md` files change.

Use it if you frequently edit notes in Obsidian while also using Claude.

### Install (macOS)

```bash
chmod +x scripts/install-file-watcher.sh
./scripts/install-file-watcher.sh
```

The installer detects your Python/venv path, installs `watchdog` if needed, and loads the LaunchAgent. Starts on login and restarts if it crashes.

### Manual Test

```bash
source .venv/bin/activate
python scripts/watch_notes.py
```

Edit a note file—you should see "rebuilding index..." in the watcher output.

### Check Status

```bash
launchctl list | grep zettelkasten.watcher

# View logs
tail -f ~/.local/share/mcp/zettelkasten/watcher.log
```

### Uninstall

```bash
./scripts/install-file-watcher.sh --uninstall
```

---

## Recommended System Prompt

Add the system prompt from `docs/SYSTEM_PROMPT.md` to your Claude preferences. This enables:

- Automatic knowledge capture during conversations
- Cluster emergence detection at conversation start
- Proper Zettelkasten workflows (search before create, link immediately)

---

## Tools Reference

### Core Note Operations

| Tool | Description |
|------|-------------|
| `zk_create_note` | Create atomic notes (fleeting/literature/permanent/structure/hub) |
| `zk_get_note` | Retrieve note by ID or title |
| `zk_update_note` | Update existing notes |
| `zk_delete_note` | Delete notes |

### Linking

| Tool | Description |
|------|-------------|
| `zk_create_link` | Create semantic links between notes |
| `zk_remove_link` | Remove links |
| `zk_get_linked_notes` | Get notes linked to/from a note |

### Search & Discovery

| Tool | Description |
|------|-------------|
| `zk_search_notes` | Search by text, tags, or type |
| `zk_find_similar_notes` | Find notes similar to a given note |
| `zk_find_central_notes` | Find most connected notes |
| `zk_find_orphaned_notes` | Find unconnected notes |
| `zk_list_notes_by_date` | List notes by date range |
| `zk_get_all_tags` | List all tags |

### Cluster Analysis

| Tool | Description |
|------|-------------|
| `zk_get_cluster_report` | Get pending clusters needing structure notes |
| `zk_create_structure_from_cluster` | Create structure note from cluster |
| `zk_refresh_clusters` | Regenerate cluster analysis |
| `zk_dismiss_cluster` | Permanently dismiss cluster from suggestions |

### Maintenance

| Tool | Description |
|------|-------------|
| `zk_rebuild_index` | Rebuild database index from files |

---

## Prompts Reference

MCP prompts are workflow templates accessible via Claude's prompt picker.

| Prompt | Description | Use When |
|--------|-------------|----------|
| `knowledge_creation` | Process information into 3-5 atomic notes | Adding articles, ideas, or notes |
| `knowledge_creation_batch` | Process larger volumes into 5-10 notes | Processing books or long-form content |
| `knowledge_exploration` | Map connections to existing knowledge | Exploring how topics relate |
| `knowledge_synthesis` | Create higher-order insights | Finding bridges between ideas |

### Example Usage

In Claude Desktop, select a prompt from the prompt picker, then provide the required input:

**knowledge_creation**: Paste an article or your notes, get atomic notes with links.

**knowledge_exploration**: Enter a topic to map its connections.

**knowledge_synthesis**: Provide context to spark connections between unrelated areas.

---

## Link Types

| Type | Use When | Inverse |
|------|----------|---------|
| `reference` | Generic "see also" connection | reference |
| `extends` | Building on another idea | extended_by |
| `refines` | Clarifying or improving | refined_by |
| `contradicts` | Opposing view | contradicted_by |
| `questions` | Raising questions about | questioned_by |
| `supports` | Providing evidence for | supported_by |
| `related` | Loose thematic connection | related |

---

## Note Types

| Type | Purpose |
|------|---------|
| `fleeting` | Quick captures, unprocessed thoughts |
| `literature` | Ideas from sources with citation |
| `permanent` | Refined ideas in your own words |
| `structure` | Maps organizing 7-15 related notes on a specific topic |
| `hub` | Domain overview linking to structure notes; entry point for navigating a broad area of knowledge |

**Structure vs. Hub:** A structure note organizes a cluster of permanent notes around a single topic — it is a curated map one level above the notes themselves. A hub note operates one level higher still: it links to structure notes (and occasionally key permanent notes) across an entire knowledge domain. Where a structure note answers "what do I know about X?", a hub note answers "how is my knowledge of this whole domain organized?" Most Zettelkastens need only a handful of hub notes.

---

## File Format

Notes are stored as Markdown files with YAML frontmatter:

```markdown
---
id: "20251217T172432480464000"
title: "Poetry Revision Principles"
type: structure
tags:
  - poetry
  - revision
  - craft
created: "2025-12-17T17:24:32"
updated: "2025-12-17T17:24:32"
---

# Poetry Revision Principles

Content here...

## Links
- reference [[20250728T125429845760000]] Member of structure
```

You can edit these files directly in any text editor or Obsidian. Run `zk_rebuild_index` after external edits.

---

## Troubleshooting

### Server not loading in Claude Desktop

1. Check the path in `claude_desktop_config.json` is absolute (not relative)
2. Verify the venv python exists: `ls -la /path/to/.venv/bin/python`
3. Check Claude Desktop logs for errors

### Database out of sync

If notes were edited outside the MCP server:

```
zk_rebuild_index
```

### Cluster detection not running

```bash
launchctl list | grep zettelkasten.cluster-detection
# Should show: - 0 com.zettelkasten.cluster-detection

# Check logs
cat /tmp/zettelkasten-clusters.log

# Reinstall if needed
./scripts/install-cluster-detection.sh --uninstall
./scripts/install-cluster-detection.sh
```

### File watcher not running

```bash
launchctl list | grep zettelkasten.watcher
# Should show: - 0 com.zettelkasten.watcher

# Check logs
cat ~/.local/share/mcp/zettelkasten/watcher.log

# Reinstall if needed
./scripts/install-file-watcher.sh --uninstall
./scripts/install-file-watcher.sh
```

---

## Development

```bash
# Run tests
pytest

# Run with debug logging
ZETTELKASTEN_LOG_LEVEL=DEBUG python -m zettelkasten_mcp

# Run cluster detection manually
python scripts/detect_clusters.py
```

---

## CLI Tool

The `zk` command provides terminal access for mechanical operations:

```bash
zk status          # Overview of notes, tags, orphans, pending clusters
zk search <query>  # Find notes by text
zk clusters        # Show pending structure note candidates
zk orphans         # List unconnected notes
zk rebuild         # Rebuild index (add --clusters to refresh cluster analysis)
zk export <id>     # Export note markdown to stdout
zk tags            # List all tags with usage counts
```

Install: `pipx install --editable .` (adds `zk` to your PATH)

---

## License

MIT
