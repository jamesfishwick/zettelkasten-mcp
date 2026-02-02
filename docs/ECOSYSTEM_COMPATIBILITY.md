# Ecosystem Compatibility

Not Obsidian-specific. Uses standard YAML frontmatter + markdown.

## Requirements

**Read-only:**
- Markdown viewer
- File browser

**Full compatibility:**
- YAML frontmatter parser
- Wikilink recognition `[[note_id]]`
- File system access

## File Format

```markdown
---
id: 20250728T123456000001
title: Note Title
type: permanent
tags: [tag1, tag2]
created: 2025-07-28T12:34:56.000001
updated: 2025-07-28T12:34:56.000001
---

# Note Title

Content here...

## Links
- extends [[20250727T111111]] Builds on this idea
- supports [[20250726T222222]] Evidence for that
```

**Key points:**
- ID-based wikilinks survive renames
- Semantic link types (extends, supports, contradicts, questions, refines, related)
- Plain text, no proprietary formats

## Tool Compatibility

| Tool | Support | Navigation | Notes |
|------|---------|------------|-------|
| Obsidian | Full | ✅ | Wikilinks + YAML native |
| VS Code + Foam | Full | ✅ | Install Foam extension |
| Logseq | Full | ✅ | Outliner-first interface |
| Zettlr | Full | ✅ | Academic writing focus |
| Typora | Read | ❌ | No link navigation |
| VS Code (plain) | Read | ⚠️ | Cmd+click, relative paths only |
| GitHub | Read | ❌ | Renders markdown |
| iA Writer | Read | ❌ | Clean editor |
| Any text editor | Read | ❌ | Plain text always works |

## Setup by Tool

### Obsidian
Point vault to notes directory. Wikilinks and YAML work natively. Graph view shows connections.

### VS Code + Foam
Open notes directory as workspace. Install Foam extension for wikilinks and graph view.

### Logseq
Add notes directory as graph. Daily notes focus with outliner interface.

### Zettlr
Open notes directory. Citations and export built-in.

### Plain Editors
Read-only. Open individual files for viewing or printing.

## Database is Index Only

Markdown files are source of truth. SQLite database provides fast search:
- Rebuilt from files on startup if out of sync
- Can be deleted and regenerated anytime
- Not required for reading/editing

Edit notes in any editor. MCP server detects changes via file watcher or manual rebuild.

## No Obsidian Dependencies

Uses:
- Standard YAML frontmatter
- Standard markdown
- Wikilinks (many tools support)
- Plain text files
- Flat directory structure

Does NOT use:
- Obsidian properties
- Obsidian plugins
- Dataview queries
- Proprietary formats

## Folder Structure

```
notes/
  20250728T123456000001.md
  20250727T111111000001.md
  ...
```

Flat directory of `.md` files named by IDs.

## Why Portable

1. Human-readable plain text
2. ID-based filenames (no title/path coupling)
3. Wikilinks (widely supported)
4. Standard YAML
5. Database optional

## Recommendations

**Best options:**
1. VS Code + Foam - Free, cross-platform
2. Logseq - Outliner workflow
3. Zettlr - Academic writing

**Read-only:**
- Any markdown viewer
- GitHub (beautiful rendering)
- Export to PDF from any editor

## Future Enhancements

Possible additions:
1. Standard markdown links `[Title](file.md)` - works everywhere, including GitHub
2. Static site generator - browse in browser, share publicly
3. Mobile apps - iOS/Android with sync

Current system already works with most tools.

## Summary

Prerequisites:
1. Folder with `.md` files
2. YAML frontmatter parser
3. Wikilink support (for navigation)

MCP server handles intelligent operations (creation, linking, clustering). Markdown tools provide viewing/editing.
