# Changelog Automation

AI-powered changelog automation using Claude Agent SDK. Automates fetching Slack updates, writing changelog content, formatting, review, and GitHub PR creation.

**Important:** This project is designed for Mintlify documentation sites and includes opinionated templates and formatting. You'll need to customize paths, structure, and brand guidelines in `servers/github_tools.py`, `main.py`, and `skills/` directories to match your organization's needs.

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
   
   Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` with your credentials:
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
- GitHub personal access token with `repo` scope
- Anthropic API key
- Slack bot with appropriate permissions (see below)

### Slack Bot Setup

Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps) with these bot token scopes:
- `channels:history`, `channels:read`, `files:read`, `users:read`

Install to workspace, copy the bot token (starts with `xoxb-`), invite the bot to your channel, and get the channel ID from channel details.

**Learn more:** [Slack Bot Setup Guide](https://api.slack.com/start/building/bolt-python)

### GitHub Token Setup

Create a personal access token at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope.

**Learn more:** [GitHub token documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

### Anthropic API Key

Get your API key from [console.anthropic.com](https://console.anthropic.com/). See [Anthropic docs](https://docs.anthropic.com/) for details.

### Environment Variables

Set these required variables:

| Variable | Description |
|---------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude Agent SDK |
| `GITHUB_TOKEN` | GitHub personal access token with repo access |
| `GITHUB_REPO` | Repository name (e.g., "your-org/your-repo") |
| `SLACK_TOKEN` | Slack bot token (starts with `xoxb-`) |
| `SLACK_CHANNEL_ID` | Slack channel ID to monitor (starts with `C`) |
| `ORCHESTRATOR_MODEL` | Claude model (e.g., "claude-sonnet-4-5") |

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

Skills provide domain expertise loaded on-demand. They differ from agent prompts in a key way:

| Use Skills For | Use Prompts For |
|----------------|-----------------|
| Procedural "how-to" knowledge | Dynamic configuration (dates, IDs) |
| Reusable across conversations | Session-specific role assignment |
| Static domain expertise | Environment-specific values |
| Auto-discovered by description | Orchestration logic |

**Current skills:**

| Skill | Purpose | Why It's a Skill |
|-------|---------|------------------|
| `brand-writing` | Voice and style guidelines | Static expertise, reused across agents |
| `changelog-formatting` | Template structure and media formatting | Procedural knowledge for consistent output |
| `doc-quality` | Documentation review criteria | Reusable review checklist |
| `media-insertion` | Inserting Slack media into markdown | Step-by-step procedure |

**What stays in prompts (not skills):**
- Time windows and dates (dynamic)
- Slack channel IDs (environment config)
- Repository names (environment config)
- Tool permission lists (session constraints)
- Orchestrator workflow (specific to this automation)

**Design principle:** Extract procedural "how-to" knowledge into skills. Keep dynamic config and role assignment in prompts. Skills auto-discover by description matching—prompts should be lean.

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

This project is opinionated and designed for a specific workflow. To adapt it for your organization:

### Required Customization

1. **Brand Guidelines** (`skills/brand-writing/BRAND_GUIDELINES.md`)
   - Replace with your organization's brand voice and style guide
   - Update product names, terminology, and messaging

2. **Documentation Structure** (`servers/github_tools.py`)
   - Update these functions to match your documentation site structure:

| Function | What to Change |
|----------|----------------|
| `update_docs_json_content()` | Navigation anchor name and grouping logic |
| `create_changelog_pr()` | Changelog path structure (default: `docs/updates/YYYY/MM/DD/changelog.mdx`) |
| `parse_changelog_path()` | Path parsing if structure differs |
| `upload_media_file()` | Image path structure (default: `docs/images/changelog/YYYY-MM-DD/`) |
| `add_changelog_frontmatter()` | Frontmatter format and components |

3. **Agent Prompts** (`main.py`)
   - Customize agent instructions to match your changelog format
   - Update references to your Slack channel structure

**Key files:** `servers/github_tools.py`, `main.py`, `skills/`

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

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

This project was built for a specific use case but can be adapted for other organizations. Contributions that make the project more flexible and easier to customize are welcome!
