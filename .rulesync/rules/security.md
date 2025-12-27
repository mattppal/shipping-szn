---
targets: ['*']
description: "Security practices, validation, and anti-patterns"
globs: ["**/*"]
---

# Security & Validation

## Environment Variables

- **Never commit** `.env` files
- Validate required vars: `if not GITHUB_TOKEN: raise ValueError(...)`
- Use descriptive names: `GITHUB_TOKEN`, `SLACK_CHANNEL_ID`, `GITHUB_REPO`

## File Path Validation

- Always validate before file operations
- Use relative paths: `./docs/updates/...`
- Prevent traversal: Validate paths don't escape allowed directories
- Parse dates from paths: Use regex (see `parse_changelog_path()` in [github_tools.py](../servers/github_tools.py))

## GitHub Operations

- Validate changelog content before PR creation
- Use draft PRs for automated changelogs
- Include review checklist in PR description
- Auto-add labels: `bot`, `automated-pr`, `needs-review`, `changelog`

## Anti-Patterns

**Don't:**

- ❌ Clone repositories (create files locally, use GitHub MCP)
- ❌ Hardcode paths (use relative from project root)
- ❌ Skip env var validation
- ❌ Expose tokens in logs/errors
- ❌ Use "we" (use "you")
- ❌ Capitalize generic terms (only Replit products)
- ❌ Write outside `./docs/updates/`
- ❌ Create PRs without validation
- ❌ Use absolute URLs in docs
- ❌ Bypass permissions without reason

