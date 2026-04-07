# Reddit Launch Post Draft

Target subreddits: r/zettelkasten, r/pkm, r/ObsidianMD, r/ClaudeAI

---

## Title

I built an MCP server that turns Claude into a Zettelkasten partner

## Body

I've been building a Zettelkasten for [TIME PERIOD] and kept running into the same friction: capturing ideas during a conversation with Claude meant copy-pasting between apps, manually creating links, and hoping I'd remember to file things properly later.

So I built **slipbox-mcp** -- an MCP server that gives Claude direct access to a Zettelkasten. It stores notes as plain Markdown files with YAML frontmatter, so they work with Obsidian, any text editor, or git.

**What it does:**

- Creates atomic notes (fleeting, literature, permanent, structure, hub) following Zettelkasten principles
- Semantic links between notes (extends, refines, contradicts, supports, questions, reference, related)
- BM25-ranked full-text search via SQLite FTS5
- Automatic cluster detection -- finds groups of related notes that might need a structure note
- Graph analysis: find central notes, orphans, similar notes
- CLI tool (`slipbox`) for quick terminal access

**How it works in practice:**

You're having a conversation with Claude about [TOPIC]. An insight comes up. Instead of breaking flow, Claude searches your existing notes, creates a new permanent note, and links it to related ideas -- all within the conversation. At the start of each session, Claude can check for emerging clusters and suggest structure notes.

**The key design decisions:**

- Plain Markdown files -- no lock-in, works with Obsidian, vim, whatever
- SQLite for indexing -- fast search without a separate service
- Seven semantic link types -- not just "related", but *how* ideas connect
- Structure notes emerge from clusters, not top-down categories

**Tech details:**

- Python 3.10+, runs as an MCP server for Claude Desktop or Claude Code
- ~220 unit tests, tool contract tests, and LLM evals
- Optional file watcher for auto-indexing when you edit in Obsidian
- MIT licensed

GitHub: [GITHUB_URL]

I'd love feedback on the approach. Has anyone else tried integrating AI with their Zettelkasten workflow?

---

## Notes for posting

- r/zettelkasten: Lead with the Zettelkasten methodology angle. Emphasize semantic links and structure note emergence.
- r/pkm: Broader framing -- "AI-assisted knowledge management". Mention Obsidian compatibility.
- r/ObsidianMD: Lead with "works with your existing Obsidian vault". Emphasize plain Markdown, file watcher.
- r/ClaudeAI: Lead with MCP server angle. Emphasize the developer experience and tool descriptions.
- Adjust tone per subreddit. r/zettelkasten is methodological; r/ClaudeAI is technical.
- Post on a weekday morning (US time) for best visibility.
- Reply to early comments quickly to boost engagement.
