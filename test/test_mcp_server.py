#!/usr/bin/env python3
"""Standalone Slack MCP server for subprocess execution.

This server provides Slack tools via MCP protocol using stdio transport.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_agent_sdk import create_sdk_mcp_server  # noqa: E402
from servers.slack_tools import fetch_messages_from_channel  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run the Slack MCP server."""
    server = create_sdk_mcp_server(name="slack", tools=[fetch_messages_from_channel])

    # Get the MCP server instance
    mcp_instance = server["instance"]

    # Run the server with stdio transport
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await mcp_instance.run(
            read_stream,
            write_stream,
            mcp_instance.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
