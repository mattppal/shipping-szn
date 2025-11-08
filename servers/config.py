import os
from dotenv import load_dotenv
from claude_agent_sdk.types import McpHttpServerConfig
from claude_agent_sdk import create_sdk_mcp_server
from servers.slack_tools import fetch_messages_from_channel
from servers.github_tools import create_changelog_pr, add_changelog_frontmatter

load_dotenv()

MCP_SERVERS = {
    "github": McpHttpServerConfig(
        type="http",
        url="https://api.githubcopilot.com/mcp/",
        headers={
            "X-MCP-Toolsets": "pull_requests,repos",
            "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN', '')}",
        },
    ),
    "mintlify": McpHttpServerConfig(
        type="http",
        url="https://mintlify.com/docs/mcp",
    ),
    "replit": McpHttpServerConfig(
        type="http",
        url="https://docs.replit.com/mcp",
    ),
    "slack_updates": create_sdk_mcp_server(
        name="slack_updates", tools=[fetch_messages_from_channel]
    ),
    "github_changelog": create_sdk_mcp_server(
        name="github_changelog",
        tools=[create_changelog_pr, add_changelog_frontmatter],
    ),
}
