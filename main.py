import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from mcp_servers import MCP_SERVERS


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert developer relations professional.",
        permission_mode="bypassPermissions",
        cwd="./",
        mcp_servers=MCP_SERVERS,
        model="claude-3-5-haiku-latest",
    )

    async for message in query(
        prompt="List all channels",
        options=options,
    ):
        print(message)


asyncio.run(main())
