"""Shared constants for cluster-tool descriptions and MCP prompt templates.

Live source of truth for the cluster tools wired in via
@mcp.tool(description=...) in server/tools/cluster_tools.py, and for the
MCP prompts registered in server/prompts.py and server/mcp_server.py.

Note/link/search tool descriptions live as docstrings on the function
bodies in server/tools/{note_tools,link_tools,search_tools}.py — those
docstrings ARE the description the LLM sees, so this file deliberately
does not duplicate them.
"""

# ---------------------------------------------------------------------------
# Cluster tools (wired in via cluster_tools.py)
# ---------------------------------------------------------------------------

SLIPBOX_GET_CLUSTER_REPORT = """\
Get pending cluster analysis for structure note creation.

Clusters are groups of notes sharing tags but lacking a structure note.
High-scoring clusters are good candidates for new structure notes.

Uses cached analysis by default. Set refresh=true to regenerate.
Cluster analysis runs automatically via cron if configured.

Scoring factors:
- Note count (7-15 is ideal, >15 is overdue)
- Orphan ratio (more orphans = more urgent)
- Internal link density (fewer links = needs structure)
- Recency (recent activity = active domain)

Args:
    min_score: Minimum cluster score 0.0-1.0 (default: 0.5)
    limit: Maximum clusters to return (default: 5)
    include_notes: Include full note list per cluster (default: false)
    refresh: Force regeneration of cluster analysis (default: false)\
"""

SLIPBOX_CREATE_STRUCTURE_FROM_CLUSTER = """\
Create a structure note from a detected cluster.

Generates a structure note organizing all notes in the cluster,
with bidirectional links to each member note.

Run slipbox_get_cluster_report first to see available clusters and their IDs.

Args:
    cluster_id: ID from cluster report (e.g. "jackson-mac-low-chance-operations")
    title: Override the suggested title (optional)
    create_links: Create bidirectional links to member notes (default: true)\
"""

SLIPBOX_REFRESH_CLUSTERS = """\
Regenerate cluster analysis and save report.

Analyzes all notes for emergent clusters based on:
- Tag co-occurrence (tags that frequently appear together)
- Connection patterns (notes that link to each other)
- Structure note coverage (which clusters already have structure notes)

Results saved to ~/.local/share/mcp/slipbox/cluster-analysis.json\
"""

SLIPBOX_DISMISS_CLUSTER = """\
Permanently dismiss a cluster from maintenance suggestions.

Use this when a cluster has been reviewed and determined not to need
a structure note, or when the user doesn't want to be reminded about it.

Args:
    cluster_id: The cluster ID to dismiss (e.g. "poetry-craft-revision")\
"""

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

PROMPT_CLUSTER_MAINTENANCE = """\
I found {active_count} knowledge cluster(s) that might benefit from structure notes.

Top candidates:
{cluster_summaries}

Would you like me to:
1. **Create a structure note** for one of these clusters? (Just name it)
2. **Show more details** about a specific cluster?
3. **Skip for now** - I'll ask again next session
4. **Dismiss permanently** - Don't ask about these specific clusters again

Just let me know which cluster interests you, or say "skip" to move on."""

PROMPT_CLUSTER_MAINTENANCE_EMPTY = (
    "No pending cluster maintenance. Your Zettelkasten is well-organized!"
)

PROMPT_CLUSTER_MAINTENANCE_ALL_DISMISSED = (
    "All detected clusters have been addressed or dismissed."
)

PROMPT_KNOWLEDGE_CREATION = """\
I've attached information I'd like to incorporate into my Zettelkasten. Please:

First, search for existing notes that might be related before creating anything new.

Then, identify 3-5 key atomic ideas from this information and for each one:
1. Create a note with an appropriate title, type, and tags
2. Draft content in my own words with proper attribution
3. Find and create meaningful connections to existing notes
4. Update any relevant structure notes

After processing all ideas, provide a summary of the notes created, connections established, and any follow-up questions you have.

---

{content}"""

PROMPT_KNOWLEDGE_CREATION_BATCH = """\
I've attached a larger text/collection of information to process into my Zettelkasten. Please:

1. First identify main themes and check my existing system for related notes and tags

2. Extract 5-10 distinct atomic ideas from this material, organized into logical clusters
   - Eliminate any concepts that duplicate my existing notes
   - Process each validated concept into a note with appropriate type, title, tags, and content
   - Create connections between related notes in this batch
   - Connect each new note to relevant existing notes in my system

3. Update or create structure notes as needed to integrate this batch of knowledge

4. Verify quality for each note:
   - Each note contains a single focused concept
   - All sources are properly cited
   - Each note has meaningful connections
   - Terminology is consistent with my existing system

Provide a summary of all notes created, connections established, and structure notes updated, along with any areas you've identified for follow-up work.

---

{content}"""

PROMPT_KNOWLEDGE_EXPLORATION = """\
I'd like to explore how this information connects to my existing Zettelkasten. Please:

1. Identify the central concepts in this information and find related notes in my system

2. Examine knowledge hubs in my Zettelkasten by:
   - Finding central notes related to these concepts
   - Mapping their connections and similar notes
   - Identifying promising knowledge paths to follow

3. Look for any gaps, contradictions, or orphaned notes that relate to these concepts

4. Create a conceptual map showing:
   - How this information fits with my existing knowledge
   - Unexpected connections discovered
   - Potential areas for development

Finally, summarize what you've learned about my Zettelkasten through this exploration and highlight the most valuable insights found.

---

Topic/concept to explore: {topic}"""

PROMPT_KNOWLEDGE_SYNTHESIS = """\
I've attached information that might help synthesize ideas in my Zettelkasten. Please:

1. Find opportunities for synthesis by identifying:
   - Potential bridges between currently unconnected areas in my system
   - Contradictions that this information might help resolve
   - Incomplete chains of thought that could now be extended

2. For the most promising synthesis opportunities (3-5 max):
   - Create new permanent notes capturing the higher-order insights
   - Connect these synthesis notes to the contributing notes with appropriate link types
   - Update or create structure notes as needed

3. Identify any relevant fleeting notes that should be converted to permanent notes in light of this synthesis

4. Based on this synthesis work, highlight:
   - New questions that have emerged
   - Knowledge gaps revealed
   - Potential applications of the new understanding

Provide a summary of the insights discovered, notes created, and connections established through this synthesis process.

---

{content}"""

PROMPT_ANALYZE_NOTE = """\
Analyze this note for integration into my Zettelkasten. Use the slipbox tools to ground your suggestions in my actual knowledge base.

## 1. Atomicity Check

Does the note contain exactly one idea? If multiple concepts are present:
- List each distinct idea that should be its own note
- Identify the primary idea vs. supporting details
- Search first to flag any that duplicate existing notes

## 2. Connectivity Analysis

**Do this before suggesting connections:**
1. Extract 2-3 key terms from the note
2. Run `slipbox_search_notes` for each term to find related existing notes
3. Run `slipbox_find_similar_notes` if this is an existing note ID
4. Check `slipbox_find_central_notes` to see if this relates to a knowledge hub

**Then report:**
- Specific existing notes this should link to (with IDs and titles)
- Recommended link types for each connection:
  - `extends` \u2014 builds on the target note
  - `refines` \u2014 clarifies or improves the target
  - `contradicts` \u2014 presents opposing view
  - `questions` \u2014 raises doubts about the target
  - `supports` \u2014 provides evidence for the target
  - `related` \u2014 loose thematic connection

## 3. Clarity Enhancement

Rewrite the note to:
- Express one idea clearly and completely
- Stand alone without external context
- Use terminology consistent with existing notes (check related notes for conventions)
- Stay within 3-7 paragraphs

Provide the rewritten version in a code block for easy copying.

## 4. Metadata Suggestions

**Tags:** Run `slipbox_get_all_tags` first. Suggest 3-5 tags, preferring existing tags over new ones. If proposing a new tag, justify why existing tags don't fit.

**Title:** Propose a clear, searchable title that expresses the core idea.

**Note type:**
- `fleeting` \u2014 raw capture, needs processing
- `literature` \u2014 extracted from a source. REQUIRES at least one entry in `references`. Use `fleeting` if you don't have the citation yet.
- `permanent` \u2014 refined idea in user's own words
- `structure` \u2014 organizes 7-15 related notes on a topic
- `hub` \u2014 entry point to a major knowledge domain

## 5. Emergent Insights

Based on what you found in the slipbox:
- Questions this note raises that aren't answered by existing notes
- Gaps in the knowledge graph this could help fill
- Unexpected connections to distant topics in the slipbox
- Potential cluster this belongs to (check if related notes share tags but lack a structure note)

---

## Output Format

```
### Atomicity: [PASS | SPLIT NEEDED]
[analysis]

### Connections Found
| Existing Note | Link Type | Reason |
|---------------|-----------|--------|
| [title] (ID)  | extends   | ...    |

### Suggested Tags
[from existing taxonomy, or justified new tags]

### Proposed Title
[title]

### Note Type
[type with rationale]

### Rewritten Note
[clean version ready for slipbox_create_note]

### Emergent Insights
[questions, gaps, unexpected connections]
```

---

Note to analyze:

{content}"""
