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
from servers.slack_tools import fetch_messages_from_channel, mark_messages_processed
from servers.github_tools import add_changelog_frontmatter, create_changelog_pr
from util.messages import display_message

load_dotenv()

# Model configuration
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "sonnet")
FAST_MODEL = os.getenv("FAST_MODEL", "haiku")
HIGH_POWER_MODEL = os.getenv("HIGH_POWER_MODEL", "opus")

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

DEFAULT_DAYS_BACK = 14
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
            permissions["search_replit"],  # Find relevant doc links
        ],

        # template_formatter: Reformats draft to match template
        # NEEDS: Read/write/edit today's file, frontmatter tool
        # DOES NOT NEED: Slack, GitHub, search, other files
        "template_formatter": [
            f"Read({today_file})",
            f"Write({today_file})",
            f"Edit({today_file})",
            permissions["add_changelog_frontmatter"],
        ],

        # review_and_feedback: Reviews and fixes issues in changelog
        # NEEDS: Read/edit today's file
        # DOES NOT NEED: Write (edit is sufficient), Slack, GitHub, broad access
        # OPTIONAL: Search tools for verification (keeping for link validation)
        "review_and_feedback": [
            f"Read({today_file})",
            f"Edit({today_file})",
            permissions["search_replit"],  # Validate doc links
            permissions["search_mintlify"],  # Validate doc links
        ],

        # pr_writer: Creates GitHub PR, marks Slack messages as processed
        # NEEDS: PR tool, Slack mark tool, read today's file (for timestamps)
        # DOES NOT NEED: Write/edit (PR tool handles uploads), glob, broad access
        "pr_writer": [
            permissions["create_changelog_pr"],
            permissions["mark_messages_processed"],
            f"Read({today_file})",  # Read timestamps from first line
        ],
    }


# Build permission groups at module load time
permission_groups = build_permission_groups()


USER_PROMPT = """You are the orchestrator for creating and shipping a product changelog.

Delegate concrete work to subagents and coordinate end-to-end:
    1. changelog_writer: fetch updates from Slack and draft the changelog file (raw content)
    2. template_formatter: reformat the changelog to match template structure
    3. review_and_feedback: review copy/tone/accuracy and suggest or apply improvements (after the changelog is formatted)
    4. pr_writer: create a branch, commit the formatted changelog file, and open a GitHub PR

Guidance and constraints:
    - Use configured MCP servers to fetch data and take actions. Do not use external CLIs.
    - Do NOT clone the repository. Create files locally, then use the GitHub MCP server for git + PR actions.

Plan the sequence, route tasks to the appropriate subagent, verify outputs between steps, and finish when the PR is open and ready for review.

Assume subagents have all relevant information required to begin work.
"""


def cleanup_existing_changelog() -> None:
    """Remove today's changelog file if it exists to ensure a clean run."""
    today_file = get_today_changelog_file()
    if os.path.exists(today_file):
        os.remove(today_file)
        print(f"Removed existing changelog: {today_file}")


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
                    - Time window: {(datetime.now() - timedelta(days=DEFAULT_DAYS_BACK)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}
                    - Channel: {os.getenv('SLACK_CHANNEL_ID')}
                    - Output: ./docs/updates/{datetime.now().strftime('%Y-%m-%d')}.md

                    Steps:
                    1. fetch_messages_from_channel(channel_id, days_back={DEFAULT_DAYS_BACK})
                    2. Write raw content with Slack permalinks per entry
                    3. First line MUST be: <!-- slack_timestamps: ts1,ts2,ts3 -->

                    See media-insertion skill for adding images from Slack response.
                    See brand-writing skill for voice/tone.
                """,
                model=FAST_MODEL,
                tools=permission_groups["changelog_writer"],
            ),
            "template_formatter": AgentDefinition(
                description="Reformat changelog content to match the changelog template structure",
                prompt=f"""
                    Reformat ./docs/updates/{datetime.now().strftime('%Y-%m-%d')}.md to match template.

                    Use add_changelog_frontmatter tool for frontmatter.
                    Follow changelog-formatting skill exactly - it has the complete template, examples, and checklist.

                    Key requirements:
                    - Preserve slack_timestamps comment (first line)
                    - Remove all Slack links from output
                    - Remove H1 headings and horizontal rules
                """,
                model=FAST_MODEL,
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
                model=HIGH_POWER_MODEL,
                tools=permission_groups["review_and_feedback"],
            ),
            "pr_writer": AgentDefinition(
                description="Draft a PR using our brand guidelines and changelog format",
                prompt=f"""
                    1. create_changelog_pr(changelog_path=./docs/updates/{datetime.now().strftime('%Y-%m-%d')}.md)
                       Repository: {os.getenv('GITHUB_REPO')}

                    2. After PR created, mark Slack messages processed:
                       - Parse timestamps from first line: <!-- slack_timestamps: ts1,ts2,ts3 -->
                       - mark_messages_processed(channel_id={os.getenv('SLACK_CHANNEL_ID')}, message_timestamps=[...])
                """,
                model=FAST_MODEL,
                tools=permission_groups["pr_writer"],
            ),
        },
        system_prompt="You are an expert developer relations professional.",
        # bypassPermissions allows autonomous execution without manual approval.
        # Security is enforced by each agent's tightly-scoped tool list (see permission_groups).
        permission_mode="bypassPermissions",
        model=ORCHESTRATOR_MODEL,
        cwd="./",
        setting_sources=None,
        mcp_servers={**MCP_SERVERS, "native_tools": NATIVE_TOOLS_SERVER},
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt=USER_PROMPT)

        async for message in client.receive_response():
            display_message(message)


asyncio.run(main())
