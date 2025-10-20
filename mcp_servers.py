import os
import sys
import dotenv
from claude_agent_sdk.types import McpHttpServerConfig, McpStdioServerConfig

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
    # Slack MCP Server (subprocess stdio server)
    # TODO: https://github.com/anthropics/claude-agent-sdk-python/issues/207#issuecomment-3390445122
    "slack": McpStdioServerConfig(
        type="stdio",
        command=sys.executable,  # Use current Python interpreter
        args=[os.path.join(os.path.dirname(__file__), "slack_mcp_server.py")],
        env={
            "SLACK_MCP_TOKEN": os.getenv("SLACK_MCP_TOKEN", ""),
        },
    ),
}
