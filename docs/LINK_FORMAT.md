# Link Format Compatibility

## Current Format: Wikilinks

This Zettelkasten uses `[[note-id]]` wikilink syntax for inter-note links.

### Example Note Structure

```markdown
---
id: 20250728T123456
title: My Note Title
type: permanent
tags: [poetry, craft]
created: 2025-07-28T12:34:56
updated: 2025-07-28T12:34:56
---

# My Note Title

Content here...

## Links
- reference [[20250727T111111]] Related concept
- extends [[20250726T222222]] Builds on this idea
```

### Why ID-Based Links?

- **Stable**: Links never break when you rename a note's title
- **No collisions**: Timestamp IDs are unique
- **Zettelkasten tradition**: Luhmann used numeric IDs

---

## Tool Compatibility

### Wikilinks `[[id]]` (Current)

| Tool | Read files | Navigate links | Graph view |
|------|------------|----------------|------------|
| Obsidian | ✅ | ✅ | ✅ |
| Foam (VS Code) | ✅ | ✅ | ✅ |
| Logseq | ✅ | ✅ | ✅ |
| Zettlr | ✅ | ✅ | ✅ |
| VS Code (plain) | ✅ | ❌ | ❌ |
| Typora | ✅ | ❌ | ❌ |
| GitHub | ✅ | ❌ | ❌ |

### Standard Markdown `[title](path)` (Future Option)

| Tool | Read files | Navigate links | Graph view |
|------|------------|----------------|------------|
| Obsidian | ✅ | ✅ | ✅ |
| Foam (VS Code) | ✅ | ✅ | ✅ |
| Logseq | ✅ | ✅ | ✅ |
| Zettlr | ✅ | ✅ | ✅ |
| VS Code (plain) | ✅ | ✅ (Cmd+click) | ❌ |
| Typora | ✅ | ✅ | ❌ |
| GitHub | ✅ | ✅ | ❌ |

---

## Future: Universal Link Format

To make links work everywhere, we could adopt standard markdown:

```markdown
## Links
- reference [Poetry Revision](20250728T123456.md) Builds on craft principles
```

### Tradeoffs

| Aspect | Wikilinks `[[id]]` | Standard `[title](path)` |
|--------|-------------------|-------------------------|
| Universal navigation | ❌ Zettelkasten tools only | ✅ Works everywhere |
| Link survives title rename | ✅ ID never changes | ❌ Must update link text |
| Link survives file rename | ✅ ID-based | ❌ Must update path |
| Human readability | 😕 `[[20250728T123456]]` | 👍 `[Poetry Revision](...)` |
| GitHub clickable | ❌ | ✅ |

### Implementation Considerations

1. **Config option**: `link_format: wikilink | markdown`
2. **Migration tool**: Convert existing notes between formats
3. **Hybrid reading**: Parse both formats on import
4. **Title sync**: Keep link text updated when note titles change

---

## Semantic Link Types

Both formats support our semantic link types:

```markdown
# Wikilink style
- extends [[20250728T123456]] Description

# Standard markdown style
- extends [Note Title](20250728T123456.md) Description
```

Link types: `reference`, `extends`, `refines`, `contradicts`, `questions`, `supports`, `related`
