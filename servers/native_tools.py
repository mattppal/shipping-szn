"""Native tools registered via Claude Agent SDK's MCP server mechanism."""

from claude_agent_sdk import create_sdk_mcp_server, tool

from servers import slack_tools, github_tools

DEFAULT_DAYS_BACK = 14


@tool(
    name="fetch_messages_from_channel",
    description="Fetch messages from a Slack channel with media and threads",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string", "description": "The Slack channel ID"},
            "days_back": {
                "type": "integer",
                "description": "Number of days back to fetch",
                "default": 14,
            },
        },
        "required": ["channel_id"],
    },
)
async def fetch_messages_tool(channel_id: str, days_back: int = DEFAULT_DAYS_BACK):
    return await slack_tools.fetch_messages_from_channel(channel_id, days_back)


@tool(
    name="mark_messages_processed",
    description="Add processed emoji reaction to Slack messages after successful PR creation",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string", "description": "The Slack channel ID"},
            "message_timestamps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of message 'ts' values to mark as processed",
            },
        },
        "required": ["channel_id", "message_timestamps"],
    },
)
async def mark_messages_tool(channel_id: str, message_timestamps: list[str]):
    return await slack_tools.mark_messages_processed(channel_id, message_timestamps)


@tool(
    name="create_changelog_pr",
    description="Create a complete changelog PR with files and docs.json updates",
    input_schema={
        "type": "object",
        "properties": {
            "changelog_path": {
                "type": "string",
                "description": "Local path to changelog file",
            },
            "changelog_content": {
                "type": "string",
                "description": "OR provide markdown content directly",
            },
            "media_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of local media file paths (auto-discovered if not provided)",
            },
            "date_override": {
                "type": "string",
                "description": "Override date (YYYY-MM-DD)",
            },
            "pr_title": {"type": "string", "description": "Custom PR title"},
            "draft": {
                "type": "boolean",
                "description": "Create as draft PR",
                "default": True,
            },
        },
    },
)
async def create_pr_tool(
    changelog_path: str = None,
    changelog_content: str = None,
    media_files: list[str] = None,
    date_override: str = None,
    pr_title: str = None,
    draft: bool = True,
):
    return await github_tools.create_changelog_pr(
        changelog_path=changelog_path,
        changelog_content=changelog_content,
        media_files=media_files,
        date_override=date_override,
        pr_title=pr_title,
        draft=draft,
    )


@tool(
    name="add_changelog_frontmatter",
    description="Add properly formatted frontmatter to changelog content",
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Raw changelog content"},
            "date": {"type": "string", "description": "Date in format YYYY-MM-DD"},
        },
        "required": ["content", "date"],
    },
)
async def add_frontmatter_tool(content: str, date: str):
    return await github_tools.add_changelog_frontmatter(content, date)


# Create SDK MCP server for native tools
NATIVE_TOOLS_SERVER = create_sdk_mcp_server(
    name="native_tools",
    version="1.0.0",
    tools=[fetch_messages_tool, mark_messages_tool, create_pr_tool, add_frontmatter_tool],
)
