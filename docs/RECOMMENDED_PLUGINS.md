# Recommended Obsidian Plugins for Zettelkasten

These plugins enhance your Zettelkasten workflow in Obsidian.

## 🔥 Essential Plugins

### 1. **Templater**
- **Why**: Auto-generate timestamps and IDs
- **Setup**: Create template with `{{date:YYYYMMDDTHHmmss}}000000000`
- **Usage**: Hotkey to insert new note template
- **Install**: Community Plugins → Search "Templater"

### 2. **Unique Note Creator**
- **Why**: Creates notes with timestamp IDs automatically
- **Setup**: Set format to match your pattern
- **Usage**: One command to create properly formatted note
- **Alternative to**: Manual ID generation

### 3. **Dataview**
- **Why**: Query your notes like a database
- **Example**: Find all permanent notes from this week
```dataview
TABLE created, title
FROM ""
WHERE type = "permanent" 
AND created >= date(today) - dur(7 days)
SORT created DESC
```

## 📊 Enhanced Workflows

### 4. **Graph Analysis**
- **Why**: Find structural holes in your knowledge
- Shows orphaned notes
- Identifies highly connected hubs
- Community detection

### 5. **Note Refactor**
- **Why**: Split long notes into atomic ones
- Extract selection to new note
- Maintains links automatically
- Perfect for processing literature notes

### 6. **Breadcrumbs**
- **Why**: Visualize hierarchy and trails
- Shows semantic link types
- Creates trail guides
- Alternative graph views

## 🎨 Quality of Life

### 7. **Calendar**
- **Why**: See when notes were created
- Visual timeline of knowledge building
- Quick access to notes by date
- Track daily note creation

### 8. **Quick Add**
- **Why**: Capture fleeting notes fast
- Mobile-friendly capture
- Pre-configured note types
- Template shortcuts

### 9. **Natural Language Dates**
- **Why**: Type "today" instead of full date
- Works in templates
- Human-readable date entry
- Auto-converts to ISO format

## 🔧 Zettelkasten-Specific Settings

### Configure These Plugins:

**Templater Settings**:
```javascript
// Timestamp ID generator
module.exports = () => {
  const now = new Date();
  const timestamp = now.toISOString()
    .replace(/[-:]/g, '')
    .replace('T', 'T')
    .replace(/\..+/, '');
  return timestamp + '000000000';
}
```

**Dataview Queries for Zettelkasten**:

Find orphaned notes:
```dataview
LIST
FROM ""
WHERE length(file.inlinks) = 0 
AND length(file.outlinks) = 0
```

Recent fleeting notes to process:
```dataview
TABLE created, title
FROM ""
WHERE type = "fleeting"
SORT created DESC
LIMIT 10
```

Notes without type:
```dataview
LIST
FROM ""
WHERE !type
```

## 🚀 Power User Combo

**Templater + QuickAdd + Dataview**:
1. QuickAdd captures fleeting notes with Templater template
2. Dataview dashboard shows notes to process
3. Refactor plugin helps split into atomic notes

## 💡 Start Simple

Begin with just:
1. **Templater** (for IDs)
2. **Calendar** (for overview)
3. **Dataview** (for queries)

Add others as your workflow evolves!

## ⚠️ Note on Compatibility

Your existing notes work with all these plugins because they follow standard:
- Markdown format
- YAML frontmatter
- Wiki-link syntax

No changes needed to your current notes!
