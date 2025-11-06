---
name: changelog-formatting
description: Format changelog content according to Replit's changelog template structure. Use when converting raw changelog content into properly structured documentation with correct frontmatter, sections, and media formatting.
---

# Changelog Formatting Skill

This skill helps you format changelog content according to Replit's template structure.

## Overview

Convert raw changelog content into properly structured documentation following:
1. Correct frontmatter with date and metadata
2. Proper section organization (Platform updates vs Teams and Enterprise)
3. Correct media path formatting and Frame wrappers
4. Consistent formatting and style

## Quick Start

### 1. Add Frontmatter

Use the `add_changelog_frontmatter` tool - don't write frontmatter manually:

```python
# The tool will create:
---
title: October 30, 2025
description: 2 min read
---

import { AuthorCard } from '/snippets/author-card.mdx';

<AuthorCard/>
```

### 2. Categorize Updates

Organize content into two main sections:

- **Platform updates**: General features, tools, improvements
- **Teams and Enterprise**: SSO, SAML, SCIM, Identity, Access Management, Viewer Seats, Groups, Permissions

### 3. Structure Content

Each section should have:
- Bullet summaries at top: `* [Update Name]`
- Detailed sections below: `### [Update Name]` with full content

### 4. Format Media

Convert local media paths to public paths:
```
./media/YYYY-MM-DD/filename → /images/changelog/YYYY-MM-DD/filename
```

Wrap all media in `<Frame>` tags:

**Images:**
```jsx
<Frame>
  <img src="/images/changelog/2025-01-15/feature.png" alt="Descriptive alt text" />
</Frame>
```

**Videos:**
```jsx
<Frame>
  <video src="/images/changelog/2025-01-15/demo.mp4" controls />
</Frame>
```

## For Complete Reference

- [CHANGELOG_TEMPLATE.md](CHANGELOG_TEMPLATE.md) - Full template structure
- [DOCS_STYLE_GUIDE.md](DOCS_STYLE_GUIDE.md) - Complete documentation style guidelines

## Key Reminders

- Only edit when content actually changes
- Preserve brand voice and style from original content
- Ensure all media has descriptive alt text
- Keep formatting consistent throughout
