# Zettelkasten Quick Reference

## 🆕 Create New Note

### 1. Generate ID

**Format**: `20250621T143022000000000.md`

- Year + Month + Day + T + Hour + Minute + Second + zeros
- Example: 2025-06-21 at 2:30:22 PM → `20250621T143022000000000.md`

### 2. Add Frontmatter

```yaml
---
created: '2025-06-21T14:30:22.000000'
id: 20250621T143022000000000
tags:
- tag1
- tag2
title: Note Title
type: permanent
updated: '2025-06-21T14:30:22.000000'
---
```

### 3. Write Content

```markdown
# Note Title

One atomic idea here...

## Links
- extends [[other_note_id]] Why this extends it
- supports [[another_id]] How this supports it
```

## 🏷️ Quick Type Guide

- **permanent**: Your developed thoughts
- **fleeting**: Quick captures
- **literature**: From reading (cite source!)
- **structure**: Topic overviews
- **hub**: Major entry points

## 🔗 Link Types

```markdown
- extends [[id]]     → Builds on idea
- supports [[id]]    → Provides evidence
- contradicts [[id]] → Opposes idea
- questions [[id]]   → Raises doubts
- refines [[id]]     → Clarifies
- related [[id]]     → General connection
```

## ⌨️ Obsidian Shortcuts

- `[[` → Start linking
- `Cmd+Click` → Open in new tab
- `Cmd+P` → Command palette
- `Cmd+O` → Quick open
- `Option+Click` → Preview

## 📝 Example Note

```yaml
---
created: '2025-06-21T15:45:00.000000'
id: 20250621T154500000000000
tags:
- api-design
- best-practices
title: REST API Versioning Strategy
type: permanent
updated: '2025-06-21T15:45:00.000000'
---

# REST API Versioning Strategy

URL path versioning (e.g., /v1/users) provides the clearest API evolution strategy for public APIs, despite the URL pollution it creates.

Key benefits:
- Immediately visible in requests
- Easy to route at load balancer
- Clear deprecation path

Trade-offs considered against header versioning and content negotiation.

## Links
- extends [[20250619T124114971223000]] Builds on API design principles
- contradicts [[20250619T132751007295000]] Challenges the "one API" philosophy
- related [[20250619T100005262822000]] Part of contract testing considerations
```

## 🎯 Daily Practice

1. **Capture** → Fleeting note (just get it down)
2. **Process** → Develop into permanent note
3. **Connect** → Add links to related notes
4. **Review** → Check backlinks panel

---
*Save this in your vault for quick reference!*
