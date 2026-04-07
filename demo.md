# slipbox-mcp: Agentic Knowledge Management

*2026-03-18T00:10:14Z by Showboat 0.6.1*
<!-- showboat-id: e3436a94-5c7c-429b-9cb7-13b920f65a44 -->

slipbox-mcp is a Model Context Protocol server that gives Claude an active role in managing a Zettelkasten knowledge system. Instead of passively assisting with note-taking, Claude creates atomic notes, forms semantic links, and detects emergent knowledge clusters.

Notes are stored as plain markdown files with YAML frontmatter — readable and editable in any tool (Obsidian, Foam, Logseq, etc.). A SQLite+FTS5 database provides fast full-text search and is rebuilt from files on demand.

## Project Layout

```bash
find src -name '*.py' | sort | head -20
```

```output
src/__init__.py
src/slipbox_mcp/__init__.py
src/slipbox_mcp/cli.py
src/slipbox_mcp/config.py
src/slipbox_mcp/dev.py
src/slipbox_mcp/main.py
src/slipbox_mcp/models/__init__.py
src/slipbox_mcp/models/db_models.py
src/slipbox_mcp/models/schema.py
src/slipbox_mcp/server/__init__.py
src/slipbox_mcp/server/mcp_server.py
src/slipbox_mcp/services/__init__.py
src/slipbox_mcp/services/cluster_service.py
src/slipbox_mcp/services/search_service.py
src/slipbox_mcp/services/zettel_service.py
src/slipbox_mcp/storage/__init__.py
src/slipbox_mcp/storage/base.py
src/slipbox_mcp/storage/note_repository.py
src/slipbox_mcp/utils.py
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
from slipbox_mcp.services.search_service import SearchService

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
from slipbox_mcp.services.search_service import SearchService
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
from slipbox_mcp.services.search_service import SearchService
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
from slipbox_mcp.services.cluster_service import ClusterService
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
grep 'def slipbox_' src/slipbox_mcp/server/mcp_server.py | sed 's/.*def //' | sed 's/(.*//' | sed 's/^/  /'
```

```output
  slipbox_create_note
  slipbox_get_note
  slipbox_update_note
  slipbox_delete_note
  slipbox_create_link
  slipbox_remove_link
  slipbox_search_notes
  slipbox_get_linked_notes
  slipbox_get_all_tags
  slipbox_find_similar_notes
  slipbox_find_central_notes
  slipbox_find_orphaned_notes
  slipbox_list_notes_by_date
  slipbox_rebuild_index
  slipbox_get_cluster_report
  slipbox_create_structure_from_cluster
  slipbox_refresh_clusters
  slipbox_dismiss_cluster
```

Seven semantic link types connect notes: **reference**, **extends**, **refines**, **contradicts**, **questions**, **supports**, **related**. These typed relationships let Claude navigate the knowledge graph purposefully — not just by keyword.

All notes are plain markdown files with YAML frontmatter, readable and editable in Obsidian, Foam, Logseq, or any text editor. The SQLite+FTS5 index is always rebuildable from the files.

---

## Demo Script

This section covers everything worth showing when demoing slipbox to someone. Each section shows what to say to Claude and what to point out.

---

### 1. Session Start: Proactive Maintenance

**What to say:**
```
Use the slipbox://maintenance-status resource and tell me if there's anything that needs attention.
```

**What it shows:** The MCP resource endpoint returns pending cluster data without the user asking. Explain that in a well-configured Claude Desktop setup, this could surface automatically at session start — Claude acting as a proactive knowledge manager, not just a passive assistant.

---

### 2. Full-Text Search

**What to say:**
```
Search my notes for "zettelkasten workflow" and show me the most relevant results.
```

Or with tag filtering:
```
Search for notes tagged "poetry" and "craft" about revision.
```

**What it shows:** BM25-ranked FTS5 search across 550+ notes returns in milliseconds. Point out that the results combine full-text scoring with tag filtering — not just a grep.

---

### 3. Knowledge Graph: Central Notes

**What to say:**
```
Which notes are the most connected in my Zettelkasten? Show me the top 10.
```

**What it shows:** `slipbox_find_central_notes` traverses the link graph and surfaces structural anchors. These are the notes everything else orbits. A knowledge base with no central notes is a pile of files; one with them is a network.

---

### 4. Knowledge Graph: Orphaned Notes

**What to say:**
```
Find all my orphaned notes — the ones with no connections to anything else.
```

**What it shows:** Unintegrated knowledge is waste. The orphan finder surfaces notes that were captured but never woven into the graph. Demo the follow-up action:

```
Look at the first three orphaned notes and suggest which existing notes they might connect to.
```

---

### 5. Direct Capture: Your Ideas → Atomic Notes

**What to say:**
```
I've been thinking about something. Here's my rough idea:

"When I read technical books, I tend to extract too many notes at once.
I end up with 30 fleeting notes from a single chapter and never process them.
The bottleneck isn't capture — it's integration. Maybe I should limit myself
to 3-5 notes per reading session and immediately link each one before moving on."

Capture this as a permanent note and find related notes to link it to.
```

**What it shows:** The user provides raw thinking; Claude formats it into a proper atomic note with appropriate title, tags (inferred from content and existing taxonomy), and links to related notes. Claude is a *formatting and integration layer*, not a content generator. The ideas stay yours.

---

### 6. Analyze and Improve a Note

**What to say:**
```
Use the analyze_note prompt with this note:

"Luhmann's slip-box worked because the constraints forced understanding.
You can't write an atomic note without decomposing what you read. You
can't link it without understanding how it relates to what you already know.
The method is a thinking tool disguised as a filing system. But most digital
implementations miss this — they optimize for capture speed instead of
integration depth. The real bottleneck was never writing notes down."
```

Or for an existing note:
```
Use the analyze_note prompt to evaluate note 20250612T110722584258000.
```

**What it shows:** Claude evaluates the note across five dimensions: atomicity (is it one idea?), connectivity (what should it link to, grounded in actual search results), clarity (rewritten version), metadata (tags from existing taxonomy, title, type), and emergent insights (gaps and unexpected connections). This is the quality gate — it turns rough captures into well-integrated permanent notes.

---

### 7. Source Decomposition: Article → Atomic Notes

**What to say:**
```
Use the knowledge_creation prompt with this article excerpt:

"The Zettelkasten method's power comes from its constraints. Each note must contain
exactly one idea. This forces you to understand what you've read well enough to
decompose it. Most people fail not because they don't take notes, but because their
notes are grab-bags of loosely related thoughts that can't be recombined later.

The linking requirement adds a second constraint: you must understand how a new idea
relates to what you already know. This is where learning actually happens — in the
moment of connection, not in the moment of highlight."

— From "Why Most Note-Taking Fails" by Example Author
```

**What it shows:** Claude extracts 2-3 atomic ideas from the source, searches for existing related notes first (to avoid duplication), creates literature notes with proper citation, and links them into the graph. The content comes from a source; Claude's job is decomposition and integration.

---

### 8. Conversation Distillation: Dialogue → Notes

**What to say (after a substantive discussion):**
```
We've been talking about [topic] for the last few exchanges.
Distill the key insights from our conversation into notes for my Zettelkasten.
```

**What it shows:** Claude extracts insights that emerged from the dialogue — things *you* said or conclusions *you* reached — and captures them as permanent notes. This is the highest-value workflow: conversations are where thinking happens, but they're ephemeral. The slipbox makes them durable.

**Example follow-up:**
```
Actually, the insight about X was yours, not mine. Remove that note —
I only want to capture my own thinking.
```

This demonstrates that the user controls what gets captured. Claude proposes; the user disposes.

---

### 9. Finding Similar Notes

**What to say:**
```
Find notes similar to [paste an ID from the central notes output].
```

**What it shows:** `slipbox_find_similar_notes` computes similarity from shared tags, common links, and content overlap — three signals. Lower the threshold to 0.1 to show the spectrum of similarity scores.

---

### 10. Cluster Detection

**What to say:**
```
Run a cluster analysis and show me the top clusters that need structure notes.
```

Or to refresh stale data:
```
Run slipbox_refresh_clusters and then show me the report.
```

**What it shows:** The cluster detector finds groups of co-occurring tags that lack an organizing structure note. Each cluster gets a score based on note count, orphan ratio, link density, and recency. Point out:
- A cluster with score > 0.7 is a strong signal that this topic area has grown enough to need a map.
- `include_notes=true` shows all the notes in the cluster.

---

### 11. Creating a Structure Note from a Cluster (the big demo moment)

**What to say:**
```
Take the highest-scoring cluster and create a structure note for it. Link it to all the member notes.
```

**What it shows:** `slipbox_create_structure_from_cluster` does the full scaffolding automatically: creates the structure note, writes a TODO synthesis stub, creates bidirectional `reference` links to every member note, and dismisses the cluster from future reports. This is the core value proposition: Claude turning emergent patterns into organized knowledge.

---

### 12. Browsing by Date

**What to say:**
```
Show me the 10 most recently created notes.
```

Or a date range:
```
List notes created between 2026-01-01 and 2026-03-01.
```

**What it shows:** `slipbox_list_notes_by_date` with `use_updated=true` vs `false`. Useful for reviewing what was captured during a specific project or time period.

---

### 13. Tag Taxonomy

**What to say:**
```
Show me all the tags in my Zettelkasten.
```

**What it shows:** `slipbox_get_all_tags` returns the full vocabulary alphabetically. Point out that tag consistency is a hygiene problem in any knowledge base — this is how Claude can check before creating notes with new tags. Say to Claude:

```
Before creating any new notes, check the existing tags and tell me which ones are most relevant to software architecture.
```

---

### 14. Guided Workflows via Prompts

These workflows process *your content* into the Zettelkasten. They are not content generators.

**Claude Code slash commands:**
```
/mcp__slipbox-mcp__knowledge_creation
/mcp__slipbox-mcp__knowledge_exploration
/mcp__slipbox-mcp__knowledge_synthesis
/mcp__slipbox-mcp__knowledge_creation_batch
/mcp__slipbox-mcp__analyze_note
/mcp__slipbox-mcp__cluster_maintenance
```

**`knowledge_creation`** — Process a single article, idea, or conversation excerpt:

```text
Use the knowledge_creation prompt with this text:

[paste article, your notes, or conversation excerpt here]
```

Claude searches for related existing notes first, extracts 3-5 atomic ideas, creates properly typed and tagged notes, and links them to your existing knowledge.

**`knowledge_creation_batch`** — For larger material (book chapters, long articles, collections):

```text
Use the knowledge_creation_batch prompt with this content:

[paste longer text — a book chapter, lecture transcript, etc.]
```

Extracts 5-10 ideas, eliminates duplicates of existing notes, organizes into clusters, and verifies quality. Good for processing a week's worth of highlights.

**`knowledge_exploration`** — Map how a topic connects through your existing graph:

```text
Use the knowledge_exploration prompt for the topic: "cognitive load in code review"
```

No new content created — this explores what you already have. Finds central notes, maps connections, surfaces gaps and orphans related to the topic.

**`knowledge_synthesis`** — Surface higher-order insights from existing notes:

```text
Use the knowledge_synthesis prompt to find bridges between my notes on
"API design" and "team communication"
```

Looks for connections you haven't made yet, resolves contradictions, creates synthesis notes that emerge from *your* existing knowledge — not generated from nothing.

**`analyze_note`** — Evaluate and improve a note before or after adding it:

```text
Use the analyze_note prompt with this note:

[paste note content or provide a note ID]
```

Checks atomicity, searches for real connections in your existing graph, suggests tags from your taxonomy, rewrites for clarity, and surfaces emergent insights. The quality gate between capture and integration.

**`cluster_maintenance`** — Proactive housekeeping:

```text
Use the cluster_maintenance prompt.
```

Reports clusters that have grown large enough to need structure notes. Good for starting a session.

---

### 15. Index Rebuild

**What to say:**

```text
Rebuild the database index from the markdown files.
```

**What it shows:** The SQLite index is always derivable from the flat markdown files. This is a safety guarantee: you can never lose your data, even if the DB is deleted. Edit a note in Obsidian, then rebuild to sync.

---

### Talking Points Summary

- **Claude processes your content, not generates it.** The three core workflows are: direct capture (your ideas), source decomposition (articles/books), and conversation distillation (dialogues). Claude formats, links, and integrates — the ideas stay yours.
- **Atomic notes + typed links** = a graph, not a folder. The structure emerges from the connections.
- **Five note types** enforce the Zettelkasten hierarchy: fleeting → literature → permanent → structure → hub.
- **Seven link types** (reference, extends, refines, contradicts, questions, supports, related) make relationships explicit and navigable.
- **Cluster detection** is the intelligence layer: it finds the topics your knowledge has grown into that still lack organizing structure.
- **Plain markdown files** mean zero lock-in. The DB is an index, not the source of truth.
- **MCP prompts** are reusable workflows that process input, not content generators. They encode the Zettelkasten method so you don't have to re-explain it every session.

---

## Screenshot Guide for README

Capture these 10 screenshots during a demo run. Each one tells a specific part of the story.

### 1. Proactive Maintenance Prompt (Section 1)

**Capture:** Claude's response after checking `slipbox://maintenance-status` — showing pending clusters with scores, note counts, and action options.

**Why:** Shows Claude acting as a proactive knowledge manager, not a passive assistant. This is the first thing people see and it differentiates slipbox from a note-taking app.

### 2. FTS5 Search Results (Section 2)

**Capture:** Search results for a query across 550+ notes — showing ranked results with tags, dates, and content previews.

**Why:** Demonstrates speed and relevance ranking. BM25 on a real knowledge base, not a toy example.

### 3. Central Notes / Knowledge Hubs (Section 3)

**Capture:** Top 5-10 most-connected notes with link counts. The higher the count, the more structurally important the note.

**Why:** Makes the "graph, not folder" concept tangible. These are the notes everything else orbits.

### 4. Direct Idea Capture (Section 5)

**Capture:** The user's raw paragraph of thinking, then Claude's response: formatted note with title, tags from existing taxonomy, and links to related notes it found.

**Why:** The core value proposition for personal use. Your ideas, Claude's formatting and integration. The money shot.

### 5. Note Analysis (Section 6)

**Capture:** Claude's analysis of a note showing the atomicity check, connectivity table (existing notes with suggested link types), tag suggestions from existing taxonomy, and rewritten version.

**Why:** Shows the quality gate between rough capture and polished knowledge. Claude doesn't just store — it improves.

### 6. Source Decomposition (Section 7)

**Capture:** An article excerpt being split into 2-3 atomic literature notes, each with proper citation, tags, and links to existing knowledge.

**Why:** Shows the content processing pipeline. Input: wall of text. Output: structured, linked, searchable knowledge.

### 7. Cluster Detection Report (Section 10)

**Capture:** Cluster analysis output showing 2-3 scored clusters with tags, note counts, orphan ratios, and suggested titles.

**Why:** This is the intelligence layer. The system finds emergent structure in your notes that you didn't plan.

### 8. Structure Note Creation (Section 11)

**Capture:** `slipbox_create_structure_from_cluster` output: structure note created, N/N member notes linked, cluster dismissed.

**Why:** The payoff of cluster detection. One command turns an emergent pattern into organized knowledge. The "big demo moment."

### 9. Raw Markdown File (n/a)

**Capture:** A `.md` note file open in Obsidian, VS Code, or a text editor — showing YAML frontmatter (id, title, type, tags, created), content, and `## Links` section with typed links.

**Why:** Proves the zero lock-in story. These are just files. The DB is an index, not the source of truth. Anyone can read them.

### 10. Orphaned Notes (Section 4)

**Capture:** List of unconnected notes, then Claude's follow-up suggesting which existing notes each orphan should connect to.

**Why:** Shows knowledge hygiene. Unintegrated notes are waste — the system surfaces them so nothing falls through the cracks.
