import os
import dotenv

dotenv.load_dotenv()

MCP_SERVERS = {
    # Slack MCP Server (korotovsky/slack-mcp-server)
    # Supports stdio transport by default. Requires tokens.
    "slack": {
        "command": "npx",
        "args": ["-y", "slack-mcp-server@1.1.26", "--transport", "stdio"],
        "env": {
            # "SLACK_MCP_XOXC_TOKEN": os.getenv("SLACK_MCP_XOXC_TOKEN", ""),
            # "SLACK_MCP_XOXD_TOKEN": os.getenv("SLACK_MCP_XOXD_TOKEN", ""),
            "SLACK_MCP_XOXP_TOKEN": os.getenv("SLACK_MCP_XOXP_TOKEN", ""),
            "SLACK_MCP_LOG_LEVEL": "debug",
        },
    },
    # GitHub MCP Server (github/github-mcp-server)
    "github": {
        "type": "http",
        "url": "https://api.githubcopilot.com/mcp/",
        "headers": {
            "X-MCP-Toolsets": "pull_requests,repos",
            "Authorization": "Bearer " + os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", ""),
        },
    },
    "mintlify": {"url": "https://mintlify.com/docs/mcp"},
    "replit": {"url": "https://replit.com/docs/mcp"},
}
