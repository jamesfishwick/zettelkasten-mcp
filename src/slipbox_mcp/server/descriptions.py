"""Shared constants for tool descriptions and prompt templates.

Single source of truth for all user-facing text in the MCP server.
Changing this file triggers LLM evals in CI.
Tool constants are named after the tool (uppercase snake_case).
Prompt constants are prefixed with PROMPT_.
"""

# ---------------------------------------------------------------------------
# Note tools
# ---------------------------------------------------------------------------

ZK_CREATE_NOTE = """\
Create a new atomic Zettelkasten note.

Each note should contain exactly one idea. After creating, immediately
link to related notes using zk_create_link.

Note Types:
- fleeting: Quick captures, unprocessed thoughts (process within 24-48 hours)
- literature: Ideas extracted from sources (always include citation in references)
- permanent: Refined ideas in your own words (the core of your Zettelkasten)
- structure: Maps organizing 7-15 related notes on a topic
- hub: Entry points into major knowledge domains

Best Practices:
- Title should express the idea in brief (understandable without reading content)
- Content should be 3-7 paragraphs, enough to stand alone
- Use 2-5 specific tags; prefer existing tags when they fit
- Search first (zk_search_notes) to avoid duplicating existing notes

Args:
    title: Concise title expressing the core idea
    content: Full note content in markdown
    note_type: One of fleeting/literature/permanent/structure/hub (default: permanent)
    tags: Comma-separated tags, e.g. "poetry,revision,craft"
    references: Newline-separated citations to external sources (e.g. "Ahrens, S. (2017). How to Take Smart Notes.\\nhttps://zettelkasten.de")\
"""

ZK_GET_NOTE = """\
Retrieve a note by ID or title.

Returns full note content including metadata, tags, and links.
Use this to read note contents before creating links or updates.

Args:
    identifier: Either the note ID (e.g. "20251217T172432480464000") or exact title\
"""

ZK_UPDATE_NOTE = """\
Update an existing note.

Only provided fields are updated; omitted fields remain unchanged.
Pass empty string for tags to clear all tags.
Pass empty string for references to clear all references.

Args:
    note_id: The ID of the note to update
    title: New title (optional)
    content: New content (optional)
    note_type: New type: fleeting/literature/permanent/structure/hub (optional)
    tags: New comma-separated tags, or empty string to clear (optional)
    references: New newline-separated citations, or empty string to clear (optional)\
"""

ZK_DELETE_NOTE = """\
Delete a note permanently.

Warning: This also removes all links to and from this note.
Consider updating note_type to "fleeting" instead if uncertain.

Args:
    note_id: The ID of the note to delete\
"""

# ---------------------------------------------------------------------------
# Link tools
# ---------------------------------------------------------------------------

ZK_CREATE_LINK = """\
Create a semantic link between two notes.

Links are directional: source -> target. Use bidirectional=true for
important relationships (automatically creates inverse link type).

Link Types:
- reference: Generic "see also" connection
- extends: Source builds upon target (inverse: extended_by)
- refines: Source clarifies or improves target (inverse: refined_by)
- contradicts: Source presents opposing view (inverse: contradicted_by)
- questions: Source raises questions about target (inverse: questioned_by)
- supports: Source provides evidence for target (inverse: supported_by)
- related: Loose thematic connection (symmetric)

Best Practices:
- Always add description explaining WHY notes are linked
- Use bidirectional=true for substantive relationships
- Create links immediately after creating notes

Args:
    source_id: ID of the source note (the note doing the linking)
    target_id: ID of the target note (the note being linked to)
    link_type: One of reference/extends/refines/contradicts/questions/supports/related
    description: Brief explanation of the relationship
    bidirectional: If true, creates inverse link from target to source\
"""

ZK_REMOVE_LINK = """\
Remove a link between two notes.

Args:
    source_id: ID of the source note
    target_id: ID of the target note
    bidirectional: If true, removes links in both directions\
"""

ZK_GET_LINKED_NOTES = """\
Get notes linked to or from a specific note.

Use this to explore the knowledge graph around a note.

Directions:
- outgoing: Notes this note links TO
- incoming: Notes that link TO this note
- both: All connected notes in either direction

Args:
    note_id: ID of the note to explore from
    direction: One of outgoing/incoming/both (default: both)\
"""

ZK_GET_ALL_TAGS = """\
Get all tags in the Zettelkasten.

Returns alphabetically sorted list of all tags.
Use this to find existing tags before creating new notes
to maintain tag consistency across your knowledge base.\
"""

# ---------------------------------------------------------------------------
# Search tools
# ---------------------------------------------------------------------------

ZK_SEARCH_NOTES = """\
Search for notes by text, tags, or type.

Searches across titles and content. Combine parameters for precise filtering.

Examples:
- Search by topic: query="poetry revision"
- Filter by tag: tags="craft,poetry"
- Find structure notes: note_type="structure"
- Combined: query="metaphor" tags="poetry" limit=5

Args:
    query: Text to search in titles and content (optional)
    tags: Comma-separated tags to filter by, e.g. "poetry,craft" (optional)
    note_type: Filter by type: fleeting/literature/permanent/structure/hub (optional)
    limit: Maximum results to return (default: 10)\
"""

ZK_FIND_SIMILAR_NOTES = """\
Find notes similar to a given note.

Similarity is based on shared tags, common links, and content overlap.
Useful for discovering connections you might have missed.

Args:
    note_id: ID of the reference note
    threshold: Minimum similarity score 0.0-1.0 (default: 0.3)
    limit: Maximum results (default: 5)\
"""

ZK_FIND_CENTRAL_NOTES = """\
Find the most connected notes in the Zettelkasten.

Central notes have the most incoming and outgoing links, making them
key hubs in your knowledge network. Good candidates for hub notes.

Args:
    limit: Maximum results (default: 10)\
"""

ZK_FIND_ORPHANED_NOTES = """\
Find notes with no connections to other notes.

Orphaned notes represent unintegrated knowledge. Review these periodically
to either link them to existing notes or identify candidates for deletion.\
"""

ZK_LIST_NOTES_BY_DATE = """\
List notes by creation or update date.

Useful for reviewing recent work or finding notes from a specific period.

Args:
    start_date: Start date in ISO format YYYY-MM-DD (optional)
    end_date: End date in ISO format YYYY-MM-DD (optional)
    use_updated: If true, filter by updated_at instead of created_at (default: false)
    limit: Maximum results (default: 10)\
"""

ZK_REBUILD_INDEX = """\
Rebuild the database index from markdown files.

Use this if notes were edited outside the MCP server or if the
database seems out of sync with the filesystem.\
"""

# ---------------------------------------------------------------------------
# Cluster tools
# ---------------------------------------------------------------------------

ZK_GET_CLUSTER_REPORT = """\
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

ZK_CREATE_STRUCTURE_FROM_CLUSTER = """\
Create a structure note from a detected cluster.

Generates a structure note organizing all notes in the cluster,
with bidirectional links to each member note.

Run zk_get_cluster_report first to see available clusters and their IDs.

Args:
    cluster_id: ID from cluster report (e.g. "jackson-mac-low-chance-operations")
    title: Override the suggested title (optional)
    create_links: Create bidirectional links to member notes (default: true)\
"""

ZK_REFRESH_CLUSTERS = """\
Regenerate cluster analysis and save report.

Analyzes all notes for emergent clusters based on:
- Tag co-occurrence (tags that frequently appear together)
- Connection patterns (notes that link to each other)
- Structure note coverage (which clusters already have structure notes)

Results saved to ~/.local/share/mcp/slipbox/cluster-analysis.json\
"""

ZK_DISMISS_CLUSTER = """\
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
2. Run `zk_search_notes` for each term to find related existing notes
3. Run `zk_find_similar_notes` if this is an existing note ID
4. Check `zk_find_central_notes` to see if this relates to a knowledge hub

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

**Tags:** Run `zk_get_all_tags` first. Suggest 3-5 tags, preferring existing tags over new ones. If proposing a new tag, justify why existing tags don't fit.

**Title:** Propose a clear, searchable title that expresses the core idea.

**Note type:**
- `fleeting` \u2014 raw capture, needs processing
- `literature` \u2014 extracted from a source (requires citation)
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
[clean version ready for zk_create_note]

### Emergent Insights
[questions, gaps, unexpected connections]
```

---

Note to analyze:

{content}"""
