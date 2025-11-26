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

### 4. Format Media (CRITICAL)

**Process for each media reference:**

1. **Verify the file exists first:**
   - Check if `./docs/updates/media/YYYY-MM-DD/filename` exists on the filesystem
   - If the file doesn't exist, REMOVE the reference from the markdown
   - Only process media that actually exists

2. **Convert local paths to public CDN paths:**
   ```
   ./media/YYYY-MM-DD/filename → /images/changelog/YYYY-MM-DD/filename
   ```

3. **Wrap in `<Frame>` tags with proper syntax:**

   **For Images** (.png, .jpg, .jpeg, .gif, .webp):
   ```jsx
   <Frame>
     <img src="/images/changelog/2025-01-15/feature.png" alt="Descriptive alt text" />
   </Frame>
   ```

   **For Videos** (.mp4, .mov, .webm):
   ```jsx
   <Frame>
     <video src="/images/changelog/2025-01-15/demo.mp4" controls />
   </Frame>
   ```

4. **Preserve descriptive alt text from the original markdown**

**Common Path Mistakes:**
- ❌ `./media/2025-01-15/file.png` (local path - wrong in final output)
- ❌ `./docs/updates/media/2025-01-15/file.png` (full local path - wrong)
- ❌ `/media/2025-01-15/file.png` (missing "images/changelog" - wrong)
- ✅ `/images/changelog/2025-01-15/file.png` (correct CDN path)

## Before/After Examples

### Example: Raw Input (from changelog_writer)

```markdown
## Updates for this week

We shipped a new dashboard!

![New dashboard interface](./media/2025-01-15/dashboard.png)

Also fixed some bugs in the editor.

### SAML improvements

SSO setup is now easier with better error messages.
```

### Example: Correctly Formatted Output (from template_formatter)

```markdown
---
title: January 15, 2025
description: 2 min read
---

import { AuthorCard } from '/snippets/author-card.mdx';

<AuthorCard/>

## Platform updates

* [New dashboard]
* [Editor bug fixes]

## Teams and Enterprise

* [SAML improvements]

### New dashboard

<Frame>
  <img src="/images/changelog/2025-01-15/dashboard.png" alt="New dashboard interface" />
</Frame>

We shipped a new dashboard with improved metrics visibility.

### Editor bug fixes

Fixed several bugs in the editor for a smoother experience.

### SAML improvements

SSO setup is now easier with better error messages.
```

### Example: Handling Missing Media

**Input with reference to non-existent file:**
```markdown
### Feature X

![Screenshot](./media/2025-01-15/missing-file.png)

Description of feature X.
```

**Output (missing file removed):**
```markdown
### Feature X

Description of feature X.
```

## Formatting Checklist

Before completing the formatting task, verify:

### Structure
- [ ] Frontmatter uses `add_changelog_frontmatter` tool (not manually written)
- [ ] Title format is "Month DD, YYYY" (e.g., "January 15, 2025")
- [ ] "## Platform updates" section appears first
- [ ] "## Teams and Enterprise" section appears second (only if relevant content exists)
- [ ] No duplicate section headers
- [ ] Bullet summary list appears directly after each `##` header
- [ ] Detailed `###` sections appear after all bullet summaries

### Bullet Lists
- [ ] Use `*` for bullets (not `-` or `+`)
- [ ] One blank line after section header, before first bullet
- [ ] No blank lines between bullet items
- [ ] One blank line after bullet list, before first `###` section

### Media
- [ ] All media wrapped in `<Frame>` tags
- [ ] Images use: `<Frame><img src="..." alt="..." /></Frame>`
- [ ] Videos use: `<Frame><video src="..." controls /></Frame>`
- [ ] All paths use CDN format: `/images/changelog/YYYY-MM-DD/filename`
- [ ] No markdown image syntax remains (`![alt](path)`)
- [ ] All referenced media files verified to exist
- [ ] Non-existent media references removed entirely

### Content
- [ ] Alt text is descriptive (not "image" or "screenshot")
- [ ] No typos in section headers
- [ ] Consistent capitalization per DOCS_STYLE_GUIDE.md

## For Complete Reference

- [CHANGELOG_TEMPLATE.md](CHANGELOG_TEMPLATE.md) - Full template structure
- [DOCS_STYLE_GUIDE.md](DOCS_STYLE_GUIDE.md) - Complete documentation style guidelines

## Key Reminders

- Only edit when content actually changes
- Preserve brand voice and style from original content
- Ensure all media has descriptive alt text
- Keep formatting consistent throughout
