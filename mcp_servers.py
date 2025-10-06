import os
import dotenv

dotenv.load_dotenv()

MCP_SERVERS = {
    # Slack MCP Server (korotovsky/slack-mcp-server)
    # Supports stdio transport by default. Requires tokens.
    "slack": {
        "command": "npx",
        "args": ["-y", "slack-mcp-server@1.1.25", "--transport", "stdio"],
        "env": {
            "SLACK_MCP_XOXP_TOKEN": os.getenv("SLACK_MCP_XOXP_TOKEN", ""),
            "SLACK_MCP_LOG_LEVEL": "debug",
        },
    },
    # GitHub MCP Server (github/github-mcp-server)
    "github": {
        "type": "http",
        "url": "https://api.githubcopilot.com/mcp/",
        "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv(
                "GITHUB_PERSONAL_ACCESS_TOKEN", ""
            ),
            # Optional: limit toolsets or enable all
            "GITHUB_TOOLSETS": os.getenv(
                "GITHUB_TOOLSETS", "repos,pull_requests,issues"
            ),
        },
    },
}
