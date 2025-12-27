---
targets: ['*']
description: "Documentation standards, brand voice, and content guidelines"
globs: ["**/docs/**/*.md", "**/prompts/**/*.md"]
---

# Documentation & Content Standards

**References:** See project documentation files in `prompts/` directory for complete guidelines.

## Changelog File Format

- **Path:** `./docs/updates/YYYY-MM-DD.md`
- **Frontmatter:** Include title (formatted date) and description
- **Structure:**
  - `## Platform updates` (bullet summary, then `### [Update Name]` sections)
  - `## Teams and Enterprise` (same structure)
- **Images:** Use `/images/changelog/YYYY-MM-DD/filename` (not `./media/...`)
- **Links:** Relative paths only, descriptive text (never "click here")

See [changelog_template.md](../prompts/changelog_template.md) for complete template structure.

## Brand Voice Rules

See [brand_guidelines.md](../prompts/brand_guidelines.md) for complete brand voice and style guidelines.

Key principles:
- **Person:** Second person ("you"), never first person plural ("we")
- **Products:** Capitalize Replit products (Agent, Assistant, Visual Editor, Workspace)
- **Terminology:** "publishing" not "deployment" (except deployment types in advanced settings)
- **Headings:** Sentence case
- **Numbers:** Spell out 0-9, use numerals for 10+
- **Commas:** Always use Oxford commas
- **Em-dashes:** Use — without spaces

## Documentation Style (Mintlify)

See [docs_style_guide.md](../prompts/docs_style_guide.md) for complete documentation style guidelines.

Key principles:
- Active voice, present tense, imperative mood
- Sentences under 25 words
- `monospace` for code/file names/commands
- **Bold** for UI elements and key terms on first use
- `<img>` tags with descriptive alt text
- No "click here" links

## Documentation Quality

See [good_docs.md](../prompts/good_docs.md) for principles on creating effective documentation.

