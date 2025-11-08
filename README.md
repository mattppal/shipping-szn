# Changelog Automation

AI-powered changelog automation using Claude Agent SDK. Automates fetching Slack updates, writing changelog content, formatting, review, and GitHub PR creation.

**Important:** Designed for Mintlify documentation sites. Customize paths and structure in `servers/github_tools.py` and `main.py`.

## Table of Contents

- [Quick Start](#quick-start)
- [Setup](#setup)
- [Architecture](#architecture)
- [Customization](#customization)
- [Development](#development)
- [Reference](#reference)

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set environment variables:**
   ```bash
   GITHUB_TOKEN=your_token
   GITHUB_REPO=your-org/repo-name
   SLACK_TOKEN=your_token
   SLACK_CHANNEL_ID=channel_id
   ORCHESTRATOR_MODEL=sonnet
   ```

3. **Run:**
   ```bash
   uv run python main.py
   ```

## Setup

### Prerequisites

- Python 3.13+
- `uv` package manager
- Mintlify documentation site repository
- GitHub personal access token
- Slack bot token

### Environment Variables

Set these required variables:

| Variable | Description |
|---------|-------------|
| `GITHUB_TOKEN` | GitHub personal access token |
| `GITHUB_REPO` | Repository name (e.g., "replit/docs") |
| `SLACK_TOKEN` | Slack bot token |
| `SLACK_CHANNEL_ID` | Slack channel ID to monitor |
| `ORCHESTRATOR_MODEL` | Claude model (e.g., "sonnet") |

### Installation

```bash
uv sync
uv run python main.py
```

## Architecture

### Multi-Agent System

Four specialized agents handle different tasks:

| Agent | Purpose |
|-------|---------|
| `changelog_writer` | Fetches Slack updates and drafts content |
| `template_formatter` | Formats content to match template structure |
| `review_and_feedback` | Reviews for quality, tone, and accuracy |
| `pr_writer` | Creates GitHub PRs with formatted content |

**Learn more:** [Claude Agent SDK Multi-Agent Orchestration](https://docs.anthropic.com/claude/docs/claude-agent-sdk#multi-agent-systems)

### Claude Skills

Skills provide domain expertise loaded on-demand:

- **brand-writing**: Brand voice and writing guidelines
- **changelog-formatting**: Template structure and formatting rules
- **doc-quality**: Documentation quality review criteria
- **media-insertion**: How to insert images and videos from Slack

Skills reduce context window usage (~100 tokens metadata vs thousands embedded).

**Learn more:** [Claude Agent SDK Skills Documentation](https://docs.anthropic.com/claude/docs/claude-skills)

### MCP Servers

Integrates with Model Context Protocol (MCP) servers:

- **GitHub MCP**: Pull request and repository management
- **Slack MCP**: Message fetching and threading
- **Mintlify MCP**: Documentation search
- **Replit MCP**: Replit documentation search

Custom MCP servers (`slack_updates`, `github_changelog`) use `create_sdk_mcp_server()`.

**Learn more:** [MCP Documentation](https://modelcontextprotocol.io/) | [Claude Agent SDK MCP Integration](https://docs.anthropic.com/claude/docs/mcp-integration)

## Customization

### Mintlify Configuration

Update these functions in `servers/github_tools.py`:

| Function | What to Change |
|----------|----------------|
| `update_docs_json_content()` | Navigation anchor name and grouping logic |
| `create_changelog_pr()` | Changelog path structure (default: `docs/updates/YYYY/MM/DD/changelog.mdx`) |
| `parse_changelog_path()` | Path parsing if structure differs |
| `upload_media_file()` | Image path structure (default: `docs/images/changelog/YYYY-MM-DD/`) |
| `add_changelog_frontmatter()` | Frontmatter format and components |

**Key files:** `servers/github_tools.py`, `main.py`, `skills/changelog-formatting/`

### Creating Skills

1. Create directory: `skills/your-skill-name/`
2. Add `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: your-skill-name
   description: When to use this skill
   ---
   ```
3. Add reference files as needed
4. Skills auto-discover on next run

**Learn more:** [Creating Custom Skills](https://docs.anthropic.com/claude/docs/claude-skills#creating-skills)

### Adding Agents

Add agents in `main.py`:

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

**Learn more:** [Claude Agent SDK Documentation](https://docs.anthropic.com/claude/docs/claude-agent-sdk)

## Development

### Running Locally

```bash
uv run python main.py
```

### Modifying Skills

Edit files in `skills/*/`. Changes take effect on next run without restart.

### Project Structure

```
.
├── main.py                    # Main orchestrator
├── servers/
│   ├── config.py              # MCP server configuration
│   ├── github_tools.py        # GitHub integration (custom MCP tools)
│   └── slack_tools.py         # Slack integration (custom MCP tools)
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

## Reference

### Workflow

1. Orchestrator receives prompt to create changelog
2. Routes to `changelog_writer` to fetch Slack messages
3. Routes to `template_formatter` to format content
4. Routes to `review_and_feedback` to review quality
5. Routes to `pr_writer` to create GitHub PR
6. Returns PR URL

### MCP Server Links

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Agent SDK MCP Integration](https://docs.anthropic.com/claude/docs/mcp-integration)
- [Creating Custom MCP Servers](https://docs.anthropic.com/claude/docs/mcp-integration#custom-mcp-servers)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
- [Slack MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/slack)
