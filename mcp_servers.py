import os
import dotenv
from claude_agent_sdk.types import McpHttpServerConfig
from claude_agent_sdk import create_sdk_mcp_server
from slack_tools_simple import fetch_messages_from_channel

dotenv.load_dotenv()

MCP_SERVERS = {
    # GitHub MCP Server (github/github-mcp-server)
    "github": McpHttpServerConfig(
        type="http",
        url="https://api.githubcopilot.com/mcp/",
        headers={
            "X-MCP-Toolsets": "pull_requests,repos",
            "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', '')}",
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
    "slack": create_sdk_mcp_server(name="slack", tools=[fetch_messages_from_channel]),
}
