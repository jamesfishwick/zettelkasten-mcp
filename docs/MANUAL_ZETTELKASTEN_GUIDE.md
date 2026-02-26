# Manual Zettelkasten Workflow in Obsidian

This guide shows you how to create and link notes directly in Obsidian, following the same structure as your MCP-created notes.

## 📝 Creating New Notes

### 1. Generate a Unique ID

Your notes use timestamp-based IDs. Here's how to create them:

**Format**: `YYYYMMDDTHHMMSSfffffffff` (where `f` is microseconds)

**Easy methods**:

- Use Obsidian's Templater plugin (recommended)
- Use a TextExpander/Keyboard Maestro snippet
- Manually create: `20250621T143022000000000` (just add zeros for microseconds)

### 2. Create Note with Proper Structure

Create a new note with the ID as filename: `20250621T143022000000000.md`

Add this frontmatter template:

```yaml
---
created: '2025-06-21T14:30:22.000000'
id: 20250621T143022000000000
tags:
- your-tag-here
- another-tag
title: Your Note Title Here
type: permanent
updated: '2025-06-21T14:30:22.000000'
---

# Your Note Title Here

Your note content goes here...

## Links
- extends [[note_id_here]] Description of how this extends that note
- supports [[another_id]] How this supports another idea
```

## 🏷️ Note Types

Choose the appropriate type for your note:

### **Permanent Notes** (`type: permanent`)

- Well-developed thoughts
- Your own insights
- Atomic ideas (one concept per note)
- Example: "Zero TODOs Policy for Technical Debt Prevention"

### **Fleeting Notes** (`type: fleeting`)

- Quick captures
- Temporary thoughts
- To be processed later
- Example: "Check out that article on API design"

### **Literature Notes** (`type: literature`)

- Ideas from books/articles
- Include source citation
- In your own words
- Example: "Luhmann's concept of communicative success"

### **Structure Notes** (`type: structure`)

- Overview of a topic area
- Lists related notes
- Shows connections
- Example: "API Contract Testing Overview"

### **Hub Notes** (`type: hub`)

- Major entry points
- Broad topic areas
- Links to many notes
- Example: "Technical Documentation Workflows Hub"

## 🔗 Creating Links

### Basic Wiki-Links

```markdown
This connects to [[20250612T110722584258000]] for more details.
```

### Semantic Link Types

Your system uses semantic relationships. Add these in a `## Links` section:

```markdown
## Links
- extends [[20250619T100005262822000]] Building on the contract testing foundation
- contradicts [[20250619T121856963113000]] Argues against incremental delivery
- supports [[20250619T132658898732000]] Provides evidence for multi-team challenges
- questions [[20250617T211225399282000]] Challenges the AI system design assumptions
- refines [[20250619T121607741285000]] Clarifies the consumer perspective
- related [[20250619T100018451374000]] Part of the testing tool ecosystem
```

### Link Type Guidelines

| Link Type | When to Use | Example |
|-----------|-------------|---------|
| `extends` | Building upon an idea | "This implementation extends the basic pattern" |
| `supports` | Providing evidence | "This case study supports the framework" |
| `contradicts` | Opposing viewpoint | "This challenges the previous assumption" |
| `questions` | Raising doubts | "This questions the scalability" |
| `refines` | Clarifying/improving | "This refines the definition" |
| `related` | General connection | "This relates to the broader topic" |

## 🎯 Obsidian Workflow Tips

### Quick Note Creation

1. **Hotkey Setup** (Settings → Hotkeys):
   - `Cmd+N`: Create new note
   - `Cmd+Shift+N`: Create note in new pane

2. **Template Setup**:
   - Create a template note with the frontmatter
   - Use Obsidian's Templates core plugin
   - Set hotkey for "Insert template"

### Daily Workflow

```markdown
1. Capture Phase (Fleeting Notes)
   - Quick capture: Cmd+N
   - Add minimal frontmatter
   - Brain dump the idea
   - Tag as 'to-process'

2. Processing Phase
   - Review fleeting notes
   - Develop into permanent notes
   - Create proper links
   - Update note type

3. Connection Phase
   - Review recent notes
   - Add semantic links
   - Check orphaned notes
   - Update structure notes
```

## 🔧 Useful Obsidian Settings

### For Zettelkasten Workflow

1. **Settings → Editor**:
   - ✅ "Always update internal links"
   - ✅ "Show frontmatter"

2. **Settings → Files & Links**:
   - Default location: "In folder: ." (root)
   - New link format: "Shortest path"

3. **Settings → Core Plugins**:
   - ✅ Templates
   - ✅ Graph view
   - ✅ Backlinks
   - ✅ Tag pane
   - ✅ Page preview

## 📋 Note Template

Save this as `_templates/zettelkasten-note.md`:

```yaml
---
created: '{{date:YYYY-MM-DD}}T{{time:HH:mm:ss}}.000000'
id: {{date:YYYYMMDD}}T{{time:HHmmss}}000000000
tags:
-
title:
type: permanent
updated: '{{date:YYYY-MM-DD}}T{{time:HH:mm:ss}}.000000'
---

# {{title}}



## Links
-
```

## 🚀 Advanced Tips

### Finding Orphaned Notes

Use this search to find notes without links:

```
-[[
```

### Finding Notes to Process

```
tag:fleeting OR tag:to-process
```

### Creating Structure Notes

When you have 5-10 notes on a topic:

1. Create a structure note
2. List all related notes
3. Write a brief overview
4. Identify gaps

### Regular Maintenance

- Weekly: Process fleeting notes
- Monthly: Find and connect orphans
- Quarterly: Create/update structure notes

## 💡 Remember

The power of Zettelkasten comes from:

1. **Atomic notes** - One idea per note
2. **Your own words** - Not copy-paste
3. **Dense linking** - Connect liberally
4. **Regular work** - Build daily

Your existing 58 notes follow these patterns. Study them for examples!
