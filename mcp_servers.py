import os
import dotenv
from claude_agent_sdk.types import McpHttpServerConfig, McpStdioServerConfig

dotenv.load_dotenv()

MCP_SERVERS = {
    # Slack MCP Server (korotovsky/slack-mcp-server)
    # Supports stdio transport by default. Requires tokens.
    "slack": McpStdioServerConfig(
        command="npx",
        args=["-y", "slack-mcp-server@1.1.26", "--transport", "stdio"],
        env={
            "SLACK_MCP_XOXP_TOKEN": os.getenv("SLACK_MCP_XOXP_TOKEN", ""),
            "SLACK_MCP_LOG_LEVEL": "debug",
        },
    ),
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
}
