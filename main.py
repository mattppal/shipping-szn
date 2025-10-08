import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
from mcp_servers import MCP_SERVERS


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert developer relations professional.",
        permission_mode="bypassPermissions",
        mcp_servers=MCP_SERVERS,
        model="claude-3-5-haiku-latest",
    )

    async for message in query(
        prompt="Please summarize the last 7 days of messages in the #shipping-szn channel, then draft a new PR for the ccc repository with the summary in the /updates folder with the name /updates/YYYY-MM-DD.md, reflecting the current date. Please include the date in the PR title.",
        options=options,
    ):
        print(message)


asyncio.run(main())
