# Slipbox MCP Server

Give Claude an active role in managing your knowledge. Slipbox is an [MCP server](https://modelcontextprotocol.io/) that turns Claude into a Zettelkasten partner -- creating atomic notes, forming semantic links, detecting emergent clusters, and synthesizing insights from your existing knowledge.

Your ideas in, structured knowledge out. Claude handles the formatting, linking, and integration. The ideas stay yours.

**Plain files, zero lock-in.** Notes are markdown with YAML frontmatter -- readable in Obsidian, Foam, Logseq, or any editor. The SQLite database is an index, not the source of truth. Delete it and rebuild from files anytime.

- **19 MCP tools** for notes, links, search, graph analysis, and cluster management
- **6 workflow prompts** encoding the Zettelkasten method so you don't re-explain it every session
- **BM25 full-text search** across titles and content via SQLite FTS5
- **Cluster detection** finds emergent topic groups and scaffolds structure notes
- **Seven typed links** (reference, extends, refines, contradicts, questions, supports, related)

Python 3.10+ | macOS or Linux

## In Action

### Proactive Maintenance

Claude reads the `slipbox://maintenance-status` resource at session start and surfaces clusters that need organizing.

![Proactive Maintenance](assets/screenshots/01-maintenance.png)

### Full-Text Search

BM25-ranked search across 550+ notes via `zk_search_notes`.

![FTS5 Search](assets/screenshots/02-search.png)

### Knowledge Graph: Central Notes

`zk_find_central_notes` surfaces the structural anchors of the graph -- the notes everything else orbits.

![Central Notes](assets/screenshots/03-central-notes.png)

### Direct Idea Capture

Your raw thinking in, a formatted atomic note with tags and links out. Claude formats and integrates -- the ideas stay yours.

![Idea Capture](assets/screenshots/04-idea-capture.png)

### Note Analysis

The `analyze_note` prompt evaluates atomicity, finds real connections in the existing graph, suggests tags, and rewrites for clarity.

![Note Analysis](assets/screenshots/05-analyze-note.png)

### Source Decomposition

The `knowledge_creation` prompt splits an article into atomic literature notes with proper citation and links.

![Source Decomposition](assets/screenshots/06-source-decomposition.png)

### Cluster Detection

`zk_get_cluster_report` finds groups of co-occurring tags that lack a structure note. Scored by size, orphan ratio, link density, and recency.

![Cluster Report](assets/screenshots/07-cluster-report.png)

### Structure Note Creation

`zk_create_structure_from_cluster` scaffolds a structure note, links all member notes, and dismisses the cluster.

![Structure Note](assets/screenshots/08-structure-note.png)

### Orphaned Notes

`zk_find_orphaned_notes` surfaces unintegrated knowledge -- candidates for connection or deletion.

![Orphans](assets/screenshots/10-orphans.png)

### Similar Notes

`zk_find_similar_notes` computes similarity from shared tags, common links, and content overlap -- three independent signals.

![Similar Notes](assets/screenshots/11-similar-notes.png)

### Graph Traversal

`zk_get_linked_notes` shows typed links from a hub note, grouped by link type.

![Linked Notes](assets/screenshots/12-linked-notes.png)

### Knowledge Synthesis

The `knowledge_synthesis` prompt finds bridges between unconnected areas and proposes synthesis notes from your existing knowledge.

![Knowledge Synthesis](assets/screenshots/17-knowledge-synthesis.png)

### Zero Lock-In: Plain Files in Obsidian

Notes are plain markdown. Open the vault in Obsidian and everything works -- rendered content, backlinks, and the knowledge graph.

<!-- TODO: capture manually -> assets/screenshots/obsidian-graph.png -->

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/jamesfishwick/slipbox-mcp.git
cd slipbox-mcp

pipx install --editable .
```

### 2. Configure Environment

Create a `.env` file or set environment variables:

```bash
# Where notes are stored as markdown files

export SLIPBOX_NOTES_DIR="~/.local/share/mcp/slipbox/notes"

# SQLite database path

export SLIPBOX_DATABASE_PATH="~/.local/share/mcp/slipbox/data/slipbox.db"

# Optional: Log level (DEBUG, INFO, WARNING, ERROR)

export SLIPBOX_LOG_LEVEL="INFO"
```

Or copy the example:

```bash
cp .env.example .env
# Edit .env with your paths

```

### 3. Initialize Data Directories

```bash
mkdir -p ~/.local/share/mcp/slipbox/notes
mkdir -p ~/.local/share/mcp/slipbox/data
```

The server creates these automatically, but explicit creation helps verify permissions.

### 4. Configure Claude Desktop

**macOS** — `~/Library/Application Support/Claude/claude_desktop_config.json`

**Linux** — `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "slipbox": {
      "command": "/absolute/path/to/slipbox-mcp/.venv/bin/python",
      "args": ["-m", "slipbox_mcp.main"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/slipbox-mcp/src",
        "SLIPBOX_NOTES_DIR": "/Users/yourname/.local/share/mcp/slipbox/notes",
        "SLIPBOX_DATABASE_PATH": "/Users/yourname/.local/share/mcp/slipbox/data/slipbox.db",
        "SLIPBOX_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Replace `/absolute/path/to/` and `/Users/yourname/` with your actual paths. The `PYTHONPATH` must point to the `src/` directory so Python can find the package. Environment variables set in `.env` are not read by Claude Desktop — configure them here instead.

> **Important:** `~` is NOT expanded in `claude_desktop_config.json`. Use full absolute paths for `SLIPBOX_NOTES_DIR` and `SLIPBOX_DATABASE_PATH` (e.g., `/Users/yourname/...` on macOS, `/home/yourname/...` on Linux). Using `~` will create a literal directory named `~` instead of resolving to your home directory.

**If you installed via `pipx install --editable .`**, find the Python path with:

```bash
pipx environment --value VENV
# Output: /Users/yourname/.local/share/pipx/venvs/slipbox-mcp

# Append /bin/python to get the full path

```

Use `/Users/yourname/.local/share/pipx/venvs/slipbox-mcp/bin/python` as the `command` value.

### 5. Restart Claude Desktop

Quit and reopen Claude Desktop to load the MCP server.

### 6. Verify Installation

In Claude:

- "Create a test note about something"
- "Search my slipbox for test"
- "Find orphaned notes"

---

## Optional: Automatic Cluster Detection

Cluster analysis scans all notes and computes similarity scores. Running it daily (6am) pre-computes results so `slipbox_get_cluster_report()` returns instantly. Without scheduling, cluster detection runs on-demand, which is slower for large collections.

Run manually after bulk imports, major reorganization, or when you want immediate results.

### Install Cluster Detection (macOS)

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

Output saved to `~/.local/share/mcp/slipbox/cluster-analysis.json`.

### Uninstall Cluster Detection

```bash
./scripts/install-cluster-detection.sh --uninstall
```

---

## Optional: File Watcher for Auto-Indexing

The MCP server maintains a database index for fast searching. Editing notes in Obsidian (or any editor) makes the database stale until you run `slipbox_rebuild_index`.

The file watcher runs as a background daemon, monitoring your notes directory and automatically rebuilding the index when `.md` files change.

Use it if you frequently edit notes in Obsidian while also using Claude.

### Install File Watcher (macOS)

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
launchctl list | grep slipbox.watcher

# View logs

tail -f ~/.local/share/mcp/slipbox/watcher.log
```

### Uninstall File Watcher

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
| `slipbox_create_note` | Create atomic notes (fleeting/literature/permanent/structure/hub) |
| `slipbox_get_note` | Retrieve note by ID or title |
| `slipbox_update_note` | Update existing notes |
| `slipbox_delete_note` | Delete notes |

### Linking

| Tool | Description |
|------|-------------|
| `slipbox_create_link` | Create semantic links between notes |
| `slipbox_remove_link` | Remove links |
| `slipbox_delete_link` | Delete a specific link (errors if link does not exist) |
| `slipbox_get_linked_notes` | Get notes linked to/from a note |

### Search & Discovery

| Tool | Description |
|------|-------------|
| `slipbox_search_notes` | Search by text (BM25-ranked), tags, or type |
| `slipbox_find_similar_notes` | Find notes similar to a given note |
| `slipbox_find_central_notes` | Find most connected notes |
| `slipbox_find_orphaned_notes` | Find unconnected notes |
| `slipbox_list_notes_by_date` | List notes by date range |
| `slipbox_get_all_tags` | List all tags |

### Cluster Analysis

| Tool | Description |
|------|-------------|
| `slipbox_get_cluster_report` | Get pending clusters needing structure notes |
| `slipbox_create_structure_from_cluster` | Create structure note from cluster |
| `slipbox_refresh_clusters` | Regenerate cluster analysis |
| `slipbox_dismiss_cluster` | Permanently dismiss cluster from suggestions |

### Maintenance

| Tool | Description |
|------|-------------|
| `slipbox_rebuild_index` | Rebuild database index from files |

---

## Prompts Reference

MCP prompts are reusable workflow templates that encode the Zettelkasten method so you don't re-explain it every session.

| Prompt | Description | Use When |
|--------|-------------|----------|
| `knowledge_creation` | Process information into 3-5 atomic notes | Adding articles, ideas, or notes |
| `knowledge_creation_batch` | Process larger volumes into 5-10 notes | Processing books or long-form content |
| `knowledge_exploration` | Map connections to existing knowledge | Exploring how topics relate |
| `knowledge_synthesis` | Create higher-order insights | Finding bridges between ideas |
| `analyze_note` | Evaluate a note's fitness for the slipbox | Reviewing a new or existing note |
| `cluster_maintenance` | Surface pending housekeeping | Start of a working session |

### How to Use Prompts

**Claude Code** supports prompts natively as slash commands:

```text
/mcp__slipbox-mcp__knowledge_creation
/mcp__slipbox-mcp__knowledge_exploration
/mcp__slipbox-mcp__knowledge_synthesis
/mcp__slipbox-mcp__knowledge_creation_batch
/mcp__slipbox-mcp__analyze_note
/mcp__slipbox-mcp__cluster_maintenance
```

**Claude Desktop** does not have a prompt picker UI. Invoke prompts conversationally:

```text
Use the knowledge_creation prompt with this content: [paste text]

Use the knowledge_exploration prompt for the topic: "poetry and cognitive load"

Use the cluster_maintenance prompt.
```

Claude will call the prompt template behind the scenes and fill in your input.

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

You can edit these files directly in any text editor or Obsidian. Run `slipbox_rebuild_index` after external edits.

---

## Upgrading

After pulling new versions, restart Claude Desktop. If the release notes mention database changes, run `slipbox_rebuild_index` once to bring your existing database up to date.

**Upgrading to FTS5 search (any version after the FTS5 release):** The full-text search index is created automatically when the server starts against a new database. For existing databases, the FTS5 table will be created on first startup but will be empty until you run:

```text
slipbox_rebuild_index
```

This populates the BM25 index from your existing notes. Search results will not be relevance-ranked until this is done.

---

## Troubleshooting

### Server not loading in Claude Desktop

1. Check the path in `claude_desktop_config.json` is absolute (not relative)
2. Verify the venv python exists: `ls -la /path/to/.venv/bin/python`
3. Check Claude Desktop logs for errors

### `ModuleNotFoundError: No module named 'slipbox_mcp'`

The `PYTHONPATH` in your config is missing or wrong. It must point to the `src/` directory of the cloned repo:

```json
"PYTHONPATH": "/absolute/path/to/slipbox-mcp/src"
```

### Notes directory points to `~/...` literally

If your notes directory ends up at `./~/...` relative to CWD, you used `~` in the JSON config. Claude Desktop does not expand `~`. Replace it with the full absolute path.

### Search returns no results

1. The FTS5 index may not be populated. Run `slipbox_rebuild_index` once to index existing notes.
2. If you recently edited notes outside Claude, the index may be stale. Run `slipbox_rebuild_index`.

### `slipbox_list_notes_by_date` returns empty results

If `start_date` is later than `end_date`, no notes match and an empty result is returned — this is expected behavior, not an error.

### Database out of sync

If notes were edited outside the MCP server:

```text
slipbox_rebuild_index
```

### Cluster detection not running

```bash
launchctl list | grep slipbox.cluster-detection
# Should show: - 0 com.slipbox.cluster-detection

# Check logs

cat /tmp/slipbox-clusters.log

# Reinstall if needed

./scripts/install-cluster-detection.sh --uninstall
./scripts/install-cluster-detection.sh
```

### File watcher not running

```bash
launchctl list | grep slipbox.watcher
# Should show: - 0 com.slipbox.watcher

# Check logs

cat ~/.local/share/mcp/slipbox/watcher.log

# Reinstall if needed

./scripts/install-file-watcher.sh --uninstall
./scripts/install-file-watcher.sh
```

### Upgrading from `ZETTELKASTEN_*` environment variables

If you previously used `ZETTELKASTEN_NOTES_DIR`, `ZETTELKASTEN_DATABASE_PATH`, or other `ZETTELKASTEN_*` variables, they are **no longer read**. Rename them to their `SLIPBOX_*` equivalents:

| Old | New |
|-----|-----|
| `ZETTELKASTEN_NOTES_DIR` | `SLIPBOX_NOTES_DIR` |
| `ZETTELKASTEN_DATABASE_PATH` | `SLIPBOX_DATABASE_PATH` |
| `ZETTELKASTEN_LOG_LEVEL` | `SLIPBOX_LOG_LEVEL` |
| `ZETTELKASTEN_BASE_DIR` | `SLIPBOX_BASE_DIR` |
| `ZETTELKASTEN_SERVER_NAME` | `SLIPBOX_SERVER_NAME` |

The server logs a warning if old names are detected, but does not migrate them automatically.

### Cluster report path is not configurable

The cluster analysis report always writes to `~/.local/share/mcp/slipbox/cluster-analysis.json`, regardless of `SLIPBOX_BASE_DIR` or `SLIPBOX_NOTES_DIR`. If you use non-default paths, the cluster report will still be in the default location.

### Install scripts are macOS-only

The `scripts/install-cluster-detection.sh` and `scripts/install-file-watcher.sh` scripts use `launchctl` and `~/Library/LaunchAgents/`, which only exist on macOS. On Linux, you'll need to create equivalent systemd units or cron jobs manually. See the manual test commands in the relevant README sections to verify the underlying Python scripts work on your platform.

### Default paths are relative to the working directory

If `SLIPBOX_NOTES_DIR` and `SLIPBOX_DATABASE_PATH` are not set, the server defaults to `data/notes` and `data/db/slipbox.db` **relative to the current working directory**. When running via Claude Desktop, the CWD may not be what you expect. Always set absolute paths in `claude_desktop_config.json` to avoid this.

---

## Development

### Setup

```bash
git clone https://github.com/jamesfishwick/slipbox-mcp.git
cd slipbox-mcp
uv venv && uv pip install -e ".[dev]"
```

### Testing

The project has three tiers of tests:

| Tier | Count | Speed | Cost | Command |
|------|-------|-------|------|---------|
| Unit + integration | 219 | ~2s | Free | `pytest tests/` |
| Tool contract tests | 22 | ~0.5s | Free | `pytest evals/tool_contracts/` |
| LLM evals | 28 | ~10min | ~$3-5 | `pytest evals/llm/` |

```bash
# Default: runs unit + contract tests (CI runs this)

pytest

# Run everything except LLM evals

pytest tests/ evals/tool_contracts/

# Run LLM evals (requires claude CLI authenticated)

pytest evals/llm/ -v

# Run LLM evals with a specific model

EVAL_MODEL=sonnet pytest evals/llm/ -v

# Lint

ruff check src/ evals/
```

**Unit tests** cover internal logic -- services, repository, models, parsing.

**Tool contract tests** verify the MCP tool output format that the LLM sees -- parseable structure, chaining (create -> search -> get), and helpful error messages. These are deterministic and don't call any LLM.

**LLM evals** send prompts to Claude via the `claude` CLI with the MCP server connected, then grade results by inspecting the database state (notes created, links made, tags applied). They test whether the LLM actually uses the tools correctly given the tool descriptions.

### CI/CD

**Branch protection:** Direct pushes to `main` are blocked. All changes go through PRs.

| Workflow | Trigger | Runner | What |
|----------|---------|--------|------|
| `CI` | Every PR + push to main | GitHub-hosted | Unit + contract tests, ruff |
| `LLM Evals` | PRs changing prompt files | Self-hosted | 28 LLM evals via claude CLI |

The LLM eval workflow triggers only when these files change:

- `src/slipbox_mcp/server/descriptions.py` (tool descriptions)
- `src/slipbox_mcp/server/prompts.py` (prompt templates)
- `evals/llm/**`, `evals/seed_data.py`, `evals/conftest.py`

### Customizing the eval setup

**If you don't want a self-hosted runner:** Remove `.github/workflows/llm-evals.yml` and run LLM evals locally before merging prompt changes:

```bash
pytest evals/llm/ -v
```

**If you want LLM evals on every PR** (not just prompt changes): Edit `.github/workflows/llm-evals.yml` and remove the `paths:` filter.

**To change the default eval model:** Set `EVAL_MODEL` in your environment or in the workflow file. Default is `haiku` for speed/cost.

**To set up a self-hosted runner:**

```bash
# Get a registration token

gh api repos/OWNER/REPO/actions/runners/registration-token -X POST -q '.token'

# Download and configure

mkdir -p ~/.github-runners/slipbox-mcp && cd ~/.github-runners/slipbox-mcp
curl -sL -o actions-runner.tar.gz https://github.com/actions/runner/releases/latest/download/actions-runner-osx-arm64-2.325.0.tar.gz
tar xzf actions-runner.tar.gz
./config.sh --url https://github.com/OWNER/REPO --token <TOKEN> --unattended
nohup ./run.sh &
```

### Shared prompt constants

All tool descriptions and prompt templates live in `src/slipbox_mcp/server/descriptions.py`. Both the MCP server and the eval tests import from this single source of truth. If you change a prompt, the evals test whether the LLM still behaves correctly with the new wording.

### Debug logging

```bash
SLIPBOX_LOG_LEVEL=DEBUG python -c "from slipbox_mcp.main import main; main()"
```

---

## CLI Tool

The `slipbox` command provides terminal access for mechanical operations:

```bash
slipbox status          # Overview of notes, tags, orphans, pending clusters
slipbox search <query>  # Find notes by text
slipbox clusters        # Show pending structure note candidates
slipbox orphans         # List unconnected notes
slipbox rebuild         # Rebuild index (add --clusters to refresh cluster analysis)
slipbox export <id>     # Export note markdown to stdout
slipbox tags            # List all tags with usage counts
```

Install: `pipx install --editable .` (adds `slipbox` to your PATH)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding standards, and how to submit changes.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and future direction.

## Sponsor

If slipbox-mcp is useful to you, consider [sponsoring the project](https://github.com/sponsors/jamesfishwick).

## License

MIT
