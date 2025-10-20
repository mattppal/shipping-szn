#!/usr/bin/env python3
"""Quick test to check MCP server initialization status."""

import asyncio
import os
from claude_agent_sdk import ClaudeAgentOptions, query
from mcp_servers import MCP_SERVERS

async def main():
    options = ClaudeAgentOptions(
        system_prompt="Test",
        permission_mode="bypassPermissions",
        model="claude-sonnet-4-5",
        cwd="./",
        setting_sources=["local"],
        mcp_servers=MCP_SERVERS,
    )

    print("Starting query to check MCP server status...")

    # Just get the init message
    async for message in query(
        prompt="What tools do you have access to?",
        options=options,
    ):
        print(f"Message type: {type(message).__name__}")
        if hasattr(message, 'data'):
            data = message.data
            if isinstance(data, dict) and 'mcp_servers' in data:
                print("\nMCP Server Status:")
                for server in data['mcp_servers']:
                    status_emoji = "✓" if server['status'] == 'connected' else "✗"
                    print(f"  {status_emoji} {server['name']}: {server['status']}")
                break
        break

asyncio.run(main())
