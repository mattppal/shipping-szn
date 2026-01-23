import argparse
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from claude_agent_sdk import (
    ClaudeAgentOptions,
    AgentDefinition,
    ClaudeSDKClient,
    create_sdk_mcp_server,
)

from servers.config import MCP_SERVERS
from servers.slack_tools import (
    fetch_messages_from_channel,
    mark_messages_processed,
    get_fetched_timestamps,
    clear_fetched_timestamps,
)
from servers.github_tools import add_changelog_frontmatter, create_changelog_pr
from util.messages import display_message

load_dotenv()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate changelog from Slack updates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run main.py                           # Run with defaults (14 days, skip processed)
  uv run main.py --days-back 7             # Fetch last 7 days
  uv run main.py --ignore-processed        # Include already-processed messages
  uv run main.py --days-back 7 --ignore-processed  # Both options
        """,
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=14,
        help="Number of days back to fetch messages (default: 14)",
    )
    parser.add_argument(
        "--ignore-processed",
        action="store_true",
        help="Include messages that already have the processed emoji marker",
    )
    parser.add_argument(
        "--strip-emojis",
        action="store_true",
        help="Remove :emoji: shortcodes from message text",
    )
    return parser.parse_args()

# Model configuration
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")
# Create SDK MCP server for native tools
NATIVE_TOOLS_SERVER = create_sdk_mcp_server(
    name="native_tools",
    version="1.0.0",
    tools=[
        fetch_messages_from_channel,
        mark_messages_processed,
        add_changelog_frontmatter,
        create_changelog_pr,
    ],
)

CLI_ARGS = parse_args()
DEFAULT_DAYS_BACK = CLI_ARGS.days_back
IGNORE_PROCESSED = CLI_ARGS.ignore_processed
STRIP_EMOJIS = CLI_ARGS.strip_emojis
CHANGELOG_FILE_PATTERN = "./docs/updates/{date}.md"

# Path conventions for media files:
# - changelog_writer outputs:    ./media/YYYY-MM-DD/filename (relative to changelog)
# - Actual file location:        ./docs/updates/media/YYYY-MM-DD/filename
# - template_formatter converts: /images/changelog/YYYY-MM-DD/filename (CDN path)
# - Final GitHub location:       docs/images/changelog/YYYY-MM-DD/filename


def get_today_changelog_file() -> str:
    """Get path to today's changelog file."""
    today = datetime.now().strftime("%Y-%m-%d")
    return CHANGELOG_FILE_PATTERN.format(date=today)


# Base permissions dictionary - tools and broad access patterns
permissions = {
    # Search tools (external lookups)
    "web_search": "WebSearch",
    "search_mintlify": "mcp__mintlify__SearchMintlify",
    "search_replit": "mcp__replit__SearchReplit",
    # Slack tools (native - via SDK MCP server)
    "fetch_messages_from_channel": "mcp__native_tools__fetch_messages_from_channel",
    "mark_messages_processed": "mcp__native_tools__mark_messages_processed",
    # GitHub tools (native - via SDK MCP server)
    "add_changelog_frontmatter": "mcp__native_tools__add_changelog_frontmatter",
    "create_changelog_pr": "mcp__native_tools__create_changelog_pr",
}


def build_permission_groups() -> dict[str, list[str]]:
    """Build permission groups with today's date.

    Called at runtime to ensure correct date is used.
    Each agent gets minimum required permissions (principle of least privilege).
    """
    today_file = get_today_changelog_file()

    return {
        # changelog_writer: Fetches Slack messages, creates initial draft
        # NEEDS: Slack fetch, write today's file, search for doc links
        # DOES NOT NEED: read (creating new), edit (not modifying), broad docs access
        "changelog_writer": [
            permissions["fetch_messages_from_channel"],
            f"Write({today_file})",  # Create new file only
            "Skill",
            permissions["search_replit"],  # Find relevant doc links
        ],
        # template_formatter: Reformats draft to match template
        # NEEDS: Read/write/edit today's file, frontmatter tool
        # DOES NOT NEED: Slack, GitHub, search, other files
        "template_formatter": [
            f"Read({today_file})",
            f"Write({today_file})",
            f"Edit({today_file})",
            "Skill",
            permissions["add_changelog_frontmatter"],
        ],
        # review_and_feedback: Reviews and fixes issues in changelog
        # NEEDS: Read/edit today's file
        # DOES NOT NEED: Write (edit is sufficient), Slack, GitHub, broad access
        # OPTIONAL: Search tools for verification (keeping for link validation)
        "review_and_feedback": [
            f"Read({today_file})",
            f"Edit({today_file})",
            "Skill",
            permissions["search_replit"],  # Validate doc links
            permissions["search_mintlify"],  # Validate doc links
        ],
        # pr_writer: Creates GitHub PR, marks Slack messages as processed
        # NEEDS: PR tool, Slack mark tool, read today's file (for timestamps)
        # DOES NOT NEED: Write/edit (PR tool handles uploads), glob, broad access
        "pr_writer": [
            permissions["create_changelog_pr"],
            permissions["mark_messages_processed"],
            "Skill",
            f"Read({today_file})",  # Read timestamps from first line
        ],
    }


# Build permission groups at module load time
permission_groups = build_permission_groups()


USER_PROMPT = """You are the orchestrator for creating and shipping a product changelog.

## Available Subagents

You have access to these specialized subagents. Use the Task tool with the EXACT subagent_type shown:

| subagent_type         | Purpose                                              |
|-----------------------|------------------------------------------------------|
| changelog_writer      | Fetch Slack messages and create raw changelog draft  |
| template_formatter    | Reformat changelog to match template structure       |
| review_and_feedback   | Review copy/tone/accuracy and fix issues             |
| pr_writer             | Create GitHub PR and mark Slack messages processed   |

## Workflow

Execute these steps in order using the Task tool:
1. Task(subagent_type="changelog_writer") - Fetches Slack updates and writes ./docs/updates/YYYY-MM-DD.md
2. Task(subagent_type="template_formatter") - Reformats the file to match template
3. Task(subagent_type="review_and_feedback") - Reviews and fixes copy issues
4. Task(subagent_type="pr_writer") - Creates PR and marks messages processed

## Critical Rules

- ALWAYS use the exact subagent_type values from the table above
- NEVER use subagent_type="general-purpose" - use the specialized agents
- Each subagent has its own tools and permissions - do not pass tool instructions
- Verify each step completes successfully before proceeding to the next
- Do NOT clone the repository - subagents create files locally and use GitHub MCP for PR
"""


def cleanup_existing_changelog() -> None:
    """Remove today's changelog file and any stray draft files to ensure a clean run."""
    today_file = get_today_changelog_file()
    if os.path.exists(today_file):
        os.remove(today_file)
        print(f"Removed existing changelog: {today_file}")

    # Also remove any incorrectly created draft files
    draft_files = ["draft_changelog.md", "changelog_draft.md", "draft.md"]
    for draft in draft_files:
        if os.path.exists(draft):
            os.remove(draft)
            print(f"Removed stray draft file: {draft}")


async def main():
    # Clean up any existing changelog for today before starting
    cleanup_existing_changelog()

    options = ClaudeAgentOptions(
        agents={
            "changelog_writer": AgentDefinition(
                description="Fetch updates from slack, summarize them, and add relevant links + context from the replit documentation and web search",
                prompt=f"""
                    Create changelog from Slack updates.

                    Config:
                    - Time window: {(datetime.now() - timedelta(days=DEFAULT_DAYS_BACK)).strftime('%Y-%m-%d')} to {CURRENT_DATE}
                    - Channel: {SLACK_CHANNEL_ID}

                    **CRITICAL: You MUST write the output to exactly this path:**
                    ./docs/updates/{CURRENT_DATE}.md

                    Do NOT write to any other file. Do NOT create draft files.

                    Steps:
                    1. fetch_messages_from_channel(channel_id, days_back={DEFAULT_DAYS_BACK}, ignore_processed_marker={IGNORE_PROCESSED}, strip_emojis={STRIP_EMOJIS})
                    2. Write raw content with Slack permalinks per entry to ./docs/updates/{CURRENT_DATE}.md
                    3. First line MUST be: <!-- slack_timestamps: ts1,ts2,ts3 -->

                    See media-insertion skill for adding images from Slack response.
                    See brand-writing skill for voice/tone.
                """,
                model="sonnet",
                tools=permission_groups["changelog_writer"],
            ),
            "template_formatter": AgentDefinition(
                description="Reformat changelog content to match the changelog template structure",
                prompt=f"""
                    Reformat ./docs/updates/{CURRENT_DATE}.md to match template.

                    Use add_changelog_frontmatter tool for frontmatter.
                    Follow changelog-formatting skill exactly - it has the complete template, examples, and checklist.

                    Key requirements:
                    - Preserve slack_timestamps comment (first line)
                    - Remove all Slack links from output
                    - Remove H1 headings and horizontal rules
                """,
                model="opus",
                tools=permission_groups["template_formatter"],
            ),
            "review_and_feedback": AgentDefinition(
                description="Use this agent to review copy and provide feedback on the PR",
                prompt="""
                    Review changelog against:
                    - changelog-formatting skill checklist (structure, media, no Slack links)
                    - brand-writing skill (voice, tone, capitalization)

                    Fix issues directly. Provide line-by-line corrections if needed.
                """,
                model="opus",
                tools=permission_groups["review_and_feedback"],
            ),
            "pr_writer": AgentDefinition(
                description="Draft a PR using our brand guidelines and changelog format",
                prompt=f"""
                    1. Read the changelog file to get its content
                    2. Call create_changelog_pr with these EXACT parameters:
                       - changelog_path: "./docs/updates/{CURRENT_DATE}.md"
                       - changelog_content: <the file content you read>
                       - media_files: []
                       - pr_title: "Changelog: <formatted date>"
                       - draft: true

                       **CRITICAL TYPE REQUIREMENTS:**
                       - media_files MUST be a JSON array: []
                       - Do NOT pass media_files as a string like "[]" - it must be an actual empty array
                       - Example correct call: {{"changelog_path": "...", "media_files": [], ...}}
                       - The tool will auto-discover media files from ./docs/updates/media/{CURRENT_DATE}/

                    3. After PR created, mark Slack messages processed:
                       - Parse timestamps from first line: <!-- slack_timestamps: ts1,ts2,ts3 -->
                       - mark_messages_processed(channel_id="{SLACK_CHANNEL_ID}", message_timestamps=[...])
                """,
                model="sonnet",
                tools=permission_groups["pr_writer"],
            ),
        },
        system_prompt="You are an expert developer relations professional.",
        permission_mode="bypassPermissions",
        model="sonnet",
        cwd="./",
        setting_sources=["project"],  # Load Skills from filesystem
        allowed_tools=["Skill"],  # Enable Skill tool
        mcp_servers={**MCP_SERVERS, "native_tools": NATIVE_TOOLS_SERVER},
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt=USER_PROMPT)

        async for message in client.receive_response():
            display_message(message)


asyncio.run(main())
