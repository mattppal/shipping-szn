# Mintlify changelog automation with the Claude Agent SDK

AI-powered changelog automation using Claude Agent SDK for Mintlify documentation sites. 

Automates fetching Slack updates, writing changelog content, formatting, review, and GitHub PR creation. This powers the [Replit Changelog](https://docs.replit.com/updates?utm_source=Matt&utm_medium=github&utm_campaign=mintlify-changelog)

<p align="center">
  <a href="https://replit.com/github/mattppal/shipping-szn?utm_source=Matt&utm_medium=github&utm_campaign=mintlify-changelog">
    <img src="https://replit.com/badge/github/mattppal/shipping-szn" alt="Run on Replit">
  </a>
</p>

**Important:** This project is designed for Mintlify documentation sites and includes opinionated templates and formatting.

You'll need to customize paths, structure, and brand guidelines in `servers/github_tools.py`, `main.py`, and `skills/` directories to match your organization's needs.

## Table of Contents

- [Quick Start](#quick-start)
- [Setup](#setup)
- [Architecture](#architecture)
- [Customization](#customization)
- [Development](#development)
  - [AI Rules Management](#ai-rules-management-rulesync)
- [Reference](#reference)

## Quick Start

**Deploy on Replit:** This repo is ready to run on [Replit](https://replit.com?utm_source=Matt&utm_medium=github&utm_campaign=mintlify-changelog). Click the badge above or [deploy directly](https://replit.com/github/mattppal/shipping-szn?utm_source=Matt&utm_medium=github&utm_campaign=mintlify-changelog) to get started instantly.

**Local setup:**

1. **Install dependencies:**
   ```bash
   uv sync
   pnpm i
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

- Node 24+ with `pnpm`
- Python 3.13+ with `uv`
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

### MCP Servers & Native Tools

External MCP servers for third-party integrations:

- **GitHub MCP**: Pull request and repository management
- **Mintlify MCP**: Documentation search
- **Replit MCP**: Replit documentation search

Native tools for deterministic operations (simpler, no MCP overhead):

- **fetch_messages_from_channel**: Slack message fetching with media downloads
- **mark_messages_processed**: Adds emoji reaction to processed Slack messages for idempotency
- **create_changelog_pr**: GitHub PR creation with file uploads
- **add_changelog_frontmatter**: Changelog formatting

**Why native tools?** Per [Anthropic's guidance](https://www.anthropic.com/engineering/code-execution-with-mcp), MCP is intended for scalable, agentic systems with many integrations. For deterministic, low-scale operations like these, native functions are simpler and more efficient.

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

### AI Rules Management (Rulesync)

This project uses [rulesync](https://github.com/dyoshikawa/rulesync) to manage AI coding assistant rules across multiple tools (Cursor, Claude Code). Rules are defined once in `.rulesync/` and generated for each target.

**Structure:**

```
.rulesync/
├── mcp.json          # MCP server configuration (shared)
├── .aiignore         # Files to exclude from AI context
├── rules/            # Markdown rules with YAML frontmatter
│   ├── general.md         # Project overview (root rule)
│   ├── claude-agent-sdk.md
│   ├── documentation.md
│   ├── python-code-style.md
│   ├── security.md
│   └── testing.md
└── skills/           # Claude skills (imported from .claude/skills/)
    ├── brand-writing/
    ├── changelog-formatting/
    ├── doc-quality/
    └── media-insertion/
```

**Generated outputs:**

| Target | Output Location | Files |
|--------|-----------------|-------|
| Cursor | `.cursor/rules/` | `.mdc` rule files |
| Claude Code | `.claude/` | `CLAUDE.md`, rules, skills, settings |

**Configuration (`rulesync.jsonc`):**

```jsonc
{
  "$schema": "https://raw.githubusercontent.com/dyoshikawa/rulesync/refs/heads/main/config-schema.json",
  "targets": ["cursor", "claudecode"],
  "features": ["rules", "ignore", "mcp", "skills"],
  "baseDirs": ["."]
}
```

**Automatic generation:** Configs are regenerated on `pnpm install` via the postinstall hook.

**Manual commands:**

```bash
# Import Claude skills into rulesync
npx rulesync import --targets claudecode --features skills

# Generate configs (uses rulesync.jsonc settings)
npx rulesync generate

# Initialize rulesync (first-time setup)
npx rulesync init
```

**Rule frontmatter:**

```yaml
---
targets: ['*']                    # Which tools to generate for
description: "Rule description"   # Shown in tool UI
globs: ["**/*.py"]               # File patterns this rule applies to
---
```

Only one rule should have `root: true` (currently `general.md`).

### Project Structure

```
.
├── main.py                    # Main orchestrator
├── servers/
│   ├── config.py              # External MCP server configuration
│   ├── github_tools.py        # GitHub integration (native tools)
│   └── slack_tools.py         # Slack integration (native tools)
├── skills/                    # Claude Skills (auto-discovered)
│   ├── brand-writing/
│   ├── changelog-formatting/
│   ├── doc-quality/
│   └── media-insertion/
├── util/
│   └── messages.py            # Message display utilities
├── docs/
│   └── updates/               # Generated changelogs
├── .rulesync/                 # AI rules source (edit here)
│   ├── mcp.json               # Shared MCP server config
│   ├── rules/                 # Rule definitions
│   └── skills/                # Skill definitions
├── .cursor/                   # Generated Cursor rules (don't edit)
├── .claude/                   # Generated Claude Code rules (don't edit)
├── rulesync.jsonc             # Rulesync configuration
└── pyproject.toml             # Python dependencies
```

## Reference

### Workflow

1. Orchestrator receives prompt to create changelog
2. Routes to `changelog_writer` to fetch Slack messages (14-day lookback, skips already-processed messages)
3. Routes to `template_formatter` to format content and wrap media in `<Frame>` tags
4. Routes to `review_and_feedback` to review quality
5. Routes to `pr_writer` to create GitHub PR and mark messages processed with `:summarizer_ship:` reaction
6. Returns PR URL

### Reference Links

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Agent SDK MCP Integration](https://docs.anthropic.com/claude/docs/mcp-integration)
- [Code Execution with MCP (Native Tools Guidance)](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

This project was built for a specific use case but can be adapted for other organizations. Contributions that make the project more flexible and easier to customize are welcome!
