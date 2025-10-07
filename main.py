import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from mcp_servers import MCP_SERVERS


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert developer relations professional.",
        permission_mode="bypassPermissions",
        cwd="./",
        mcp_servers=MCP_SERVERS,
    )

    async for message in query(
        prompt="Fetch the newest ships from #shipping-szn",
        options=options,
    ):
        print(message)


asyncio.run(main())
