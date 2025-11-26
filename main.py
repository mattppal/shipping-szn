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
HIGH_POWER_MODEL = os.getenv("HIGH_POWER_MODEL", "sonnet")

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


permissions = {
    # read/write/edit/glob docs (excluding media files)
    "read_docs": "Read(./docs/**/*.md)",
    "write_docs": "Write(./docs/**/*.md)",
    "edit_docs": "Edit(./docs/**/*.md)",
    "glob_docs": "Glob(./docs/**/*.md)",
    # search tools
    "web_search": "WebSearch",
    "search_mintlify": "mcp__mintlify__SearchMintlify",
    "search_replit": "mcp__replit__SearchReplit",
    # github tools (via GitHub MCP server)
    "update_pull_request": "mcp__github__update_pull_request",
    # slack tools (native - via SDK MCP server)
    "fetch_messages_from_channel": "mcp__native_tools__fetch_messages_from_channel",
    "mark_messages_processed": "mcp__native_tools__mark_messages_processed",
    # github tools (native - via SDK MCP server)
    "add_changelog_frontmatter": "mcp__native_tools__add_changelog_frontmatter",
    "create_changelog_pr": "mcp__native_tools__create_changelog_pr",
}


def get_today_changelog_permissions() -> list[str]:
    """Get permissions restricted to today's changelog file only."""
    today = datetime.now().strftime("%Y-%m-%d")
    changelog_file = CHANGELOG_FILE_PATTERN.format(date=today)
    return [
        f"Read({changelog_file})",
        f"Write({changelog_file})",
        f"Edit({changelog_file})",
    ]


permission_groups = {
    "review_and_feedback": [
        permissions["read_docs"],
        permissions["edit_docs"],
        permissions["web_search"],
        permissions["search_mintlify"],
        permissions["search_replit"],
    ],
    "changelog_writer": [
        permissions["fetch_messages_from_channel"],
        permissions["read_docs"],
        permissions["write_docs"],
        permissions["edit_docs"],
        permissions["search_replit"],
    ],
    "template_formatter": [
        *get_today_changelog_permissions(),
        permissions["add_changelog_frontmatter"],
    ],
    "pr_writer": [
        permissions["create_changelog_pr"],
        permissions["mark_messages_processed"],
        permissions["read_docs"],
        permissions["glob_docs"],
    ],
}


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


async def main():
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
