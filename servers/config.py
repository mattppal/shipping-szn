import os
from dotenv import load_dotenv
from claude_agent_sdk.types import McpHttpServerConfig

load_dotenv()

# External MCP servers for third-party integrations
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
}

# Native tools are now imported directly in main.py from:
# - servers.slack_tools: fetch_messages_from_channel
# - servers.github_tools: create_changelog_pr, add_changelog_frontmatter
