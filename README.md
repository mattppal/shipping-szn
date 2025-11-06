# Changelog Automation

An AI-powered changelog automation system using Claude Agent SDK with multi-agent orchestration and Claude Skills.

## Overview

This system automates the entire changelog creation process:
1. **Fetch** updates from Slack
2. **Write** changelog content following brand guidelines
3. **Format** according to documentation templates
4. **Review** for quality and accuracy
5. **Publish** by creating a GitHub pull request

## Architecture

### Multi-Agent System

The system uses four specialized agents orchestrated by a main coordinator:

- **changelog_writer**: Fetches Slack updates and drafts changelog content
- **template_formatter**: Reformats content to match template structure
- **review_and_feedback**: Reviews for quality, tone, and accuracy
- **pr_writer**: Creates GitHub PRs with formatted content

### Claude Skills

Skills provide domain expertise through progressive disclosure - loading content on-demand rather than embedding in prompts:

- **brand-writing** (`skills/brand-writing/`): Replit's brand voice and writing guidelines
- **changelog-formatting** (`skills/changelog-formatting/`): Template structure and formatting rules
- **doc-quality** (`skills/doc-quality/`): Documentation quality review criteria
- **media-insertion** (`skills/media-insertion/`): How to insert images and videos from Slack into markdown

**Benefits:**
- Reduced context window usage (each skill ~100 tokens metadata vs thousands embedded)
- On-demand loading (skills only load when triggered)
- Reusable across agents
- Easier to maintain and update

## Setup

### Prerequisites

- Python 3.13+
- uv package manager
- Environment variables configured (see below)

### Environment Variables

Required secrets:
```bash
GITHUB_TOKEN=          # GitHub personal access token
GITHUB_REPO=           # Repository name (e.g., "replit/docs")
SLACK_TOKEN=           # Slack bot token
SLACK_CHANNEL_ID=      # Slack channel ID to monitor
ORCHESTRATOR_MODEL=    # Claude model for orchestrator (e.g., "sonnet")
```

### Installation

```bash
# Install dependencies
uv sync

# Run the changelog automation
uv run python main.py
```

## Skills

Skills are stored in `skills/` and automatically discovered by Claude Agent SDK.

### Skill Structure

Each skill directory contains:
- `SKILL.md` - Main instructions with YAML frontmatter
- Reference files - Supporting documentation (loaded as needed)

Example:
```
skills/brand-writing/
├── SKILL.md                 # Quick reference (always loaded)
└── BRAND_GUIDELINES.md      # Full guidelines (loaded on-demand)
```

### Creating New Skills

1. Create skill directory: `skills/your-skill-name/`
2. Add `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: your-skill-name
   description: When to use this skill and what it does
   ---
   
   # Your Skill Name
   
   Quick reference content here...
   ```
3. Add reference files as needed
4. Skills are automatically discovered by the SDK

## MCP Servers

The system integrates with:
- **GitHub MCP**: Pull request and repository management
- **Slack MCP**: Message fetching and threading
- **Mintlify MCP**: Documentation search
- **Replit MCP**: Replit documentation search

## Workflow

1. Orchestrator receives user prompt to create changelog
2. Routes to `changelog_writer` → fetches Slack messages
3. Routes to `template_formatter` → formats content
4. Routes to `review_and_feedback` → reviews quality
5. Routes to `pr_writer` → creates GitHub PR
6. Returns PR URL to user

## Development

### Running Locally

```bash
# Start the automation
uv run python main.py
```

### Modifying Skills

Skills can be updated without changing code:
1. Edit files in `skills/*/`
2. Changes take effect on next run
3. No code restart required

### Adding Agents

Add new agents in `main.py`:
```python
agents={
    "agent_name": AgentDefinition(
        description="What this agent does",
        prompt="Agent instructions...",
        model="sonnet",
        tools=permission_groups["agent_permissions"],
    ),
}
```

## Project Structure

```
.
├── main.py                    # Main orchestrator
├── servers/
│   ├── config.py              # MCP server configuration
│   ├── github_tools.py        # GitHub integration
│   └── slack_tools.py         # Slack integration
├── skills/                    # Claude Skills (auto-discovered)
│   ├── brand-writing/
│   ├── changelog-formatting/
│   └── doc-quality/
├── util/
│   └── messages.py            # Message display utilities
├── docs/
│   └── updates/               # Generated changelogs
└── pyproject.toml             # Python dependencies
```

## License

Copyright © Replit
