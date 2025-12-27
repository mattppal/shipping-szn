---
root: true
targets: ['*']
description: "General project overview, structure, and common utilities"
globs: ["**/*"]
---

# Project Overview

Python-based multi-agent system using Claude Agent SDK to orchestrate changelog creation, formatting, review, and GitHub PR submission.

**Tech Stack:** Python 3.13+, `uv` package manager, `claude-agent-sdk`, `pygithub`, `slack-sdk`, `pytest`, `black`

## Project Structure

```text
ccc/
├── main.py                 # Orchestrator with agent definitions
├── servers/                # MCP server tools
│   ├── config.py          # MCP_SERVERS configuration
│   ├── github_tools.py    # GitHub API tools (@tool decorator)
│   └── slack_tools.py     # Slack API tools (@tool decorator)
├── util/                  # Utilities
│   └── messages.py        # Message display for agent responses
├── prompts/               # Agent context and guidelines
│   ├── brand_guidelines.md
│   ├── changelog_template.md
│   ├── docs_style_guide.md
│   └── good_docs.md
├── docs/updates/          # Generated changelogs (YYYY-MM-DD.md)
└── test/                  # Pytest tests (test_*.py)
```

**File placement:**

- Tools → `servers/`
- Utilities → `util/`
- Agent prompts → `prompts/`
- Changelogs → `docs/updates/YYYY-MM-DD.md`
- Media → `docs/updates/media/YYYY-MM-DD/`

## Common Utilities

### Date Handling

```python
from datetime import datetime

# File names
date_str = datetime.now().strftime("%Y-%m-%d")  # "2025-10-30"

# Display
display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")  # "Oct 30, 2025"
```

### Branch Naming

Format: `{prefix}/{timestamp}` (e.g., `changelog/20251030-143022`)

### Logging

```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Operation: {context}")
logger.error(f"Error: {error_message}")
```

## Architecture Notes

**Workflow:** Orchestrator → changelog_writer → template_formatter → review_and_feedback → pr_writer

**Permission mode:** Currently `bypassPermissions`. Change to `"explicit"` for production. See [ARCHITECTURE_REVIEW.md](../ARCHITECTURE_REVIEW.md) for details.

**Agent models:**

- Complex work: `sonnet` (changelog_writer, template_formatter)
- Simple work: `haiku` (review_and_feedback, pr_writer)

## Development Workflow

1. Review existing patterns and agent prompts
2. Follow style guide (Black, type hints, docstrings)
3. Write tests for new functionality
4. Update relevant prompts if agent behavior changes
5. Ensure security, correctness, pattern adherence

