# zettelkasten-mcp: Agentic Knowledge Management

*2026-03-18T00:10:14Z by Showboat 0.6.1*
<!-- showboat-id: e3436a94-5c7c-429b-9cb7-13b920f65a44 -->

zettelkasten-mcp is a Model Context Protocol server that gives Claude an active role in managing a Zettelkasten knowledge system. Instead of passively assisting with note-taking, Claude creates atomic notes, forms semantic links, and detects emergent knowledge clusters.

Notes are stored as plain markdown files with YAML frontmatter — readable and editable in any tool (Obsidian, Foam, Logseq, etc.). A SQLite+FTS5 database provides fast full-text search and is rebuilt from files on demand.

## Project Layout

```bash
find src -name '*.py' | sort | head -20
```

```output
src/__init__.py
src/zettelkasten_mcp/__init__.py
src/zettelkasten_mcp/cli.py
src/zettelkasten_mcp/config.py
src/zettelkasten_mcp/dev.py
src/zettelkasten_mcp/main.py
src/zettelkasten_mcp/models/__init__.py
src/zettelkasten_mcp/models/db_models.py
src/zettelkasten_mcp/models/schema.py
src/zettelkasten_mcp/server/__init__.py
src/zettelkasten_mcp/server/mcp_server.py
src/zettelkasten_mcp/services/__init__.py
src/zettelkasten_mcp/services/cluster_service.py
src/zettelkasten_mcp/services/search_service.py
src/zettelkasten_mcp/services/zettel_service.py
src/zettelkasten_mcp/storage/__init__.py
src/zettelkasten_mcp/storage/base.py
src/zettelkasten_mcp/storage/note_repository.py
src/zettelkasten_mcp/utils.py
```

## Test Suite

```bash
uv run pytest tests/ --tb=short -q 2>&1 | sed 's/passed in [0-9.]*s/passed/'
```

```output
........................................................................ [ 78%]
....................                                                     [100%]
92 passed
```

## Note Format

Every note is a plain markdown file with YAML frontmatter. Here is the frontmatter from a real note:

```bash
uv run python - <<'PYEOF'
import frontmatter
post = frontmatter.load('data/notes/20250612T110722584258000.md')
print(f"id:      {post['id']}")
print(f"title:   {post['title']}")
print(f"type:    {post['type']}")
print(f"tags:    {post['tags']}")
print(f"created: {post['created']}")
print()
print(post.content[:300])
PYEOF
```

```output
id:      20250612T110722584258000
title:   Investor-Driven AI Mandates Create Strategic Confusion
type:    permanent
tags:    ['AI-adoption', 'investor-pressure', 'strategic-consulting', 'enterprise-decision-making']
created: 2025-06-12T11:07:22.584291

# Investor-Driven AI Mandates Create Strategic Confusion

Portfolio companies face intense pressure from investors to adopt AI across all operations, often without clear business justification. This creates a "fire drill" mentality where executives scramble to demonstrate AI adoption rather than sol
```


## Knowledge Base Statistics

The data directory holds the live knowledge base — 550+ notes accumulated over months:

```bash
echo "Notes: $(ls data/notes/*.md 2>/dev/null | wc -l | tr -d ' ')" && echo "DB size: $(du -sh data/db/zettelkasten.db 2>/dev/null | cut -f1)"
```

```output
Notes: 550
DB size: 5.1M
```

## Full-Text Search (FTS5)

The SQLite FTS5 index enables BM25-ranked full-text search with BM25 ranking. Results are ordered by relevance:

```bash
uv run python - <<'PYEOF'
from zettelkasten_mcp.services.search_service import SearchService

svc = SearchService()
results = svc.search_by_text('zettelkasten')
for r in results[:5]:
    n = r.note
    tags = ', '.join(t.name for t in n.tags[:3])
    print(f'{n.id[:13]}  {n.title[:55]}')
    print(f'            [{tags}]')
PYEOF
```

```output
20260225T1719  zettelkasten-mcp: agentic knowledge management as an MC
            [zettelkasten, mcp, project]
20260225T1718  qmd and zettelkasten-mcp solve different problems in th
            [mcp, search, tool-comparison]
20250630T2133  Bridge Pattern for Dual Knowledge Systems
            [knowledge-management, workflow, obsidian]
20250630T2135  Recommendation: Hybrid Knowledge Architecture
            [recommendation, architecture-decision, knowledge-strategy]
20250630T2134  Daily Workflow with Dual Knowledge Systems
            [workflow, daily-practice, knowledge-management]
```

## Graph Analysis: Central Notes

Central notes have the most inbound and outbound links — they are the structural anchors of the knowledge graph:

```bash
uv run python - <<'PYEOF'
from zettelkasten_mcp.services.search_service import SearchService
svc = SearchService()
central = svc.find_central_notes(limit=5)
for n, count in central:
    print(f'{n.id[:13]}  {n.title[:55]} ({count} links)')
PYEOF
```

```output
20250619T1326  Contract Enforcement in Multi-Team API Development (28 links)
20250625T2018  Software Craft Evolution in AI-Assisted Development (28 links)
20251217T1724  Poetry Revision Principles (26 links)
20260227T1302  Allison Parrish: Computational Poetry and Its Tensions (24 links)
20251217T1725  Consciousness and Near-Death Experience Studies (20 links)
```

## Graph Analysis: Orphaned Notes

Notes with no links are candidates for connection — or deletion:

```bash
uv run python - <<'PYEOF'
from zettelkasten_mcp.services.search_service import SearchService
svc = SearchService()
orphans = svc.find_orphaned_notes()
print(f'Found {len(orphans)} orphaned notes:\n')
for n in orphans[:5]:
    print(f'{n.id[:13]}  {n.title[:55]}')
PYEOF
```

```output
Found 63 orphaned notes:

20250910T1356  Multi-Head Attention: Full Input Projection Not Slicing
20251022T1629  Why Aliasing rm to trash Breaks Scripts
20251228T2137  Elemental Spirits and Greek Nymph Taxonomy
20250805T0909  Sound Contradictions in Poetry - When They Work
20250904T2131  Cardinal Parental Behavior and Social Learning
```

## Cluster Detection

The cluster detector finds groups of co-occurring tags that lack a structure note to organize them. Clusters are scored by size, orphan ratio, link density, and recency — high scores are strong candidates for Claude to synthesize into structure notes:

```bash
uv run python - <<'PYEOF'
from zettelkasten_mcp.services.cluster_service import ClusterService
svc = ClusterService()
report = svc.detect_clusters()
print(f'Clusters detected: {len(report.clusters)}\n')
for c in report.clusters[:3]:
    tags = ', '.join(c.tags[:4])
    print(f'{c.suggested_title}')
    print(f'  Score: {c.score:.2f} | Notes: {c.note_count} | Orphans: {c.orphan_count}')
    print(f'  Tags: {tags}')
    print(f'  ID: {c.id}')
    print()
PYEOF
```

```output
Clusters detected: 6

Project Management Knowledge Map
  Score: 0.72 | Notes: 31 | Orphans: 0
  Tags: anti-patterns, api-design, api-development, api-testing
  ID: anti-patterns-api-design-api-development

Prompt Engineering Knowledge Map
  Score: 0.71 | Notes: 7 | Orphans: 2
  Tags: ai-prompting, evaluation, prompt-engineering, testing
  ID: ai-prompting-evaluation-prompt-engineering

Data Architecture Knowledge Map
  Score: 0.59 | Notes: 8 | Orphans: 1
  Tags: atscale, data-architecture, databricks, semantic-layer
  ID: atscale-data-architecture-databricks

```

## MCP Tools

When connected to Claude Desktop, the server exposes these tools:

```bash
grep 'def zk_' src/zettelkasten_mcp/server/mcp_server.py | sed 's/.*def //' | sed 's/(.*//' | sed 's/^/  /'
```

```output
  zk_create_note
  zk_get_note
  zk_update_note
  zk_delete_note
  zk_create_link
  zk_delete_link
  zk_search_notes
  zk_get_linked_notes
  zk_get_all_tags
  zk_find_similar_notes
  zk_find_central_notes
  zk_find_orphaned_notes
  zk_list_notes_by_date
  zk_rebuild_index
  zk_get_cluster_report
  zk_create_structure_from_cluster
  zk_refresh_clusters
  zk_dismiss_cluster
```

Seven semantic link types connect notes: **reference**, **extends**, **refines**, **contradicts**, **questions**, **supports**, **related**. These typed relationships let Claude navigate the knowledge graph purposefully — not just by keyword.

All notes are plain markdown files with YAML frontmatter, readable and editable in Obsidian, Foam, Logseq, or any text editor. The SQLite+FTS5 index is always rebuildable from the files.
