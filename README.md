# Changelog Automation

An AI-powered changelog automation system using Claude Agent SDK with multi-agent orchestration and Claude Skills.

**Important:** This changelog system is designed for Mintlify documentation sites with a custom changelog structure. Customize the code to match your Mintlify changelog structure and navigation configuration.

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

Skills provide domain expertise through progressive disclosure, loading content on-demand rather than embedding in prompts:

- **brand-writing** (`skills/brand-writing/`): Replit's brand voice and writing guidelines
- **changelog-formatting** (`skills/changelog-formatting/`): Template structure and formatting rules
- **doc-quality** (`skills/doc-quality/`): Documentation quality review criteria
- **media-insertion** (`skills/media-insertion/`): How to insert images and videos from Slack into markdown

Benefits: Reduced context window usage (~100 tokens metadata vs thousands embedded), on-demand loading, reusable across agents, easier maintenance.

## Setup

### Prerequisites

- Python 3.13+
- uv package manager
- A Mintlify documentation site repository
- Environment variables configured (see below)

### Mintlify Configuration

Customize the following to match your Mintlify changelog structure:

1. **Navigation Structure** (`docs/docs.json`): Update `update_docs_json_content()` in `servers/github_tools.py` to match your anchor name and grouping logic.

2. **Changelog Path Structure**: Default is `docs/updates/YYYY/MM/DD/changelog.mdx`. Update `create_changelog_pr()` and `parse_changelog_path()` if your structure differs.

3. **Image Path Structure**: Default is `docs/images/changelog/YYYY-MM-DD/filename`. Update `upload_media_file()` if your paths differ.

4. **Frontmatter Format**: Default includes Mintlify components like `<AuthorCard/>`. Update `add_changelog_frontmatter()` to match your requirements.

5. **File Extensions**: Default uses `.mdx`. Update `changelog_remote_path` in `create_changelog_pr()` if you use `.md`.

**Key files:** `servers/github_tools.py`, `main.py`, `skills/changelog-formatting/`

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

1. Orchestrator receives prompt to create changelog
2. Routes to `changelog_writer` to fetch Slack messages
3. Routes to `template_formatter` to format content
4. Routes to `review_and_feedback` to review quality
5. Routes to `pr_writer` to create GitHub PR
6. Returns PR URL

## Development

### Running Locally

```bash
# Start the automation
uv run python main.py
```

### Modifying Skills

Edit files in `skills/*/`. Changes take effect on next run without code restart.

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
