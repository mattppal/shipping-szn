# Overview

This is an AI-powered changelog automation system built with Claude Agent SDK. The system uses a multi-agent architecture to automate the complete changelog creation workflow: fetching updates from Slack, writing content following brand guidelines, formatting to template specifications, reviewing for quality, and publishing via GitHub pull requests.

The system leverages Claude Skills for domain expertise through progressive disclosure - loading brand guidelines, formatting rules, and quality criteria on-demand rather than embedding them in prompts. This approach significantly reduces context window usage while maintaining consistency across agents.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Multi-Agent Orchestration

The system implements a coordinator pattern with four specialized agents, each with distinct responsibilities and permissions:

**Agent Roles:**
- `changelog_writer`: Fetches Slack channel updates and drafts initial changelog content
- `template_formatter`: Reformats raw content to match Replit's documentation template structure
- `review_and_feedback`: Reviews content for quality, brand voice consistency, and accuracy
- `pr_writer`: Creates GitHub pull requests with properly formatted changelog content

**Permission Model:**
Each agent has fine-grained permissions controlling access to:
- File operations (read/write/edit specific to `./docs/updates/{date}.md`)
- External service tools (Slack, GitHub, web search)
- Documentation search capabilities (Mintlify, Replit docs)

Permissions are dynamically scoped to today's changelog file to prevent accidental modifications to existing documentation.

## Claude Skills System

Skills provide reusable domain expertise loaded on-demand via progressive disclosure. Skills are filesystem-based resources stored in `skills/` with three levels of loading:

1. **Level 1 (Metadata)**: Always loaded, ~100 tokens - skill name and description in YAML frontmatter
2. **Level 2 (Instructions)**: Loaded when triggered - main SKILL.md content
3. **Level 3 (Resources)**: Loaded as needed - reference files, templates, guidelines

**Architecture Benefits:**
- **Massive context reduction**: Skills use ~100 tokens for metadata vs 5,000+ for embedded content
- **Progressive disclosure**: Content only loads when agents trigger specific skills
- **Maintainability**: Centralized guidelines updated in one location
- **Reusability**: Multiple agents can reference the same skill
- **No code changes needed**: Skills update without modifying agent code

**Implemented Skills:**

**`brand-writing` (skills/brand-writing/):**
- SKILL.md: Quick reference for Replit's voice, tone, and style
- BRAND_GUIDELINES.md: Complete brand guidelines (loaded on-demand)
- Used by: changelog_writer, review_and_feedback agents

**`changelog-formatting` (skills/changelog-formatting/):**
- SKILL.md: Template structure and formatting rules
- CHANGELOG_TEMPLATE.md: Full MDX template
- DOCS_STYLE_GUIDE.md: Complete documentation style guide
- Used by: template_formatter agent

**`doc-quality` (skills/doc-quality/):**
- SKILL.md: Quality review checklist
- GOOD_DOCS.md: Complete documentation best practices
- Used by: review_and_feedback agent

**`media-insertion` (skills/media-insertion/):**
- SKILL.md: Complete guide for inserting Slack media into markdown
- Teaches agents how to reference downloaded images/videos
- Shows path format, alt text, and placement best practices
- Used by: changelog_writer agent (primary), template_formatter agent

**Adding New Skills:**
1. Create directory: `skills/skill-name/`
2. Add SKILL.md with YAML frontmatter and quick reference
3. Add reference files as needed
4. Skills auto-discovered by Claude Agent SDK

## MCP Server Integration

The system uses Model Context Protocol (MCP) servers to extend agent capabilities:

**HTTP-based External Servers:**
- GitHub Copilot MCP (pull requests, repo operations)
- Mintlify documentation search
- Replit documentation search

**SDK-based Custom Servers:**
- Slack tools server (fetch messages, download media)
- GitHub changelog server (PR creation, frontmatter management)

Custom MCP servers are created using `create_sdk_mcp_server()` to wrap Python async functions as tools accessible to agents.

## File Organization Strategy

**Date-based changelog files**: `docs/updates/{YYYY-MM-DD}.md`

**Media storage**: `docs/updates/media/{YYYY-MM-DD}/` for images and videos

**Configuration**: `docs/docs.json` tracks documentation structure for GitHub operations

This structure supports daily changelog generation while maintaining clear organization and preventing file conflicts.

## Tool Design Patterns

**Standalone tool functions**: Each tool is an independent async function decorated with `@tool` from Claude Agent SDK

**Error handling**: Tools implement comprehensive logging and graceful degradation (e.g., Slack API rate limits, GitHub authentication failures)

**Concurrency**: Slack media downloads use ThreadPoolExecutor with configurable parallelism (MAX_CONCURRENT_DOWNLOADS=5)

**File safety**: Filename sanitization using `python-slugify` prevents path traversal and filesystem issues

# External Dependencies

## APIs and Services

**Slack API** (`slack_sdk`):
- WebClient for channel message retrieval
- Supports threaded conversations and message history
- Downloads and stores media files locally
- Requires: `SLACK_TOKEN` environment variable

**GitHub API** (`PyGithub`):
- Repository operations (branch creation, file commits)
- Pull request management
- Tree-based commits for atomic multi-file operations
- Requires: `GITHUB_TOKEN`, `GITHUB_REPO` environment variables

**Claude Agent SDK** (`claude_agent_sdk`):
- Multi-agent orchestration
- Skill system for progressive disclosure
- Permission-based access control
- MCP server integration

## Third-Party Libraries

**Core Dependencies:**
- `python-dotenv`: Environment variable management
- `python-slugify`: Safe filename generation
- `requests`: HTTP client for file downloads

**Development Tools:**
- `uv`: Package manager (Python 3.13+)
- `asyncio`: Async/await runtime for agent coordination

## MCP Protocol

Model Context Protocol servers extend agent capabilities through standardized tool interfaces. The system supports both HTTP-based external servers (GitHub Copilot, Mintlify, Replit docs) and SDK-based custom servers wrapping Python functions.

## Data Flow

1. Slack updates → local markdown files
2. Media files → `docs/updates/media/{date}/` directory  
3. Formatted changelog → GitHub pull request
4. Skills content → loaded on-demand by agents

No database required - the system operates on filesystem-based documentation with Git as the source of truth.