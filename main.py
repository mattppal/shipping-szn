import asyncio
import os
from datetime import datetime, timedelta
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    AssistantMessage,
    SystemMessage,
    TextBlock,
    ResultMessage,
)

from mcp_servers import MCP_SERVERS


PROMPT = """
    You are the orchestrator for creating and shipping a product changelog.

    Delegate concrete work to subagents and coordinate end-to-end:
        1. changelog_writer: fetch updates from Slack and draft the changelog file
        2. review_and_feedback: review copy/tone/accuracy and suggest or apply improvements (after the changelog is written)
        3. pr_writer: create a branch, commit the changelog file, and open a GitHub PR

    Guidance and constraints:
        - Use configured MCP servers to fetch data and take actions. Do not use external CLIs.
        - Do NOT clone the repository. Create files locally, then use the GitHub MCP server for git + PR actions.

    Plan the sequence, route tasks to the appropriate subagent, verify outputs between steps, and finish when the PR is open and ready for review.
"""

# Steps:
# 1. Fetch updates from slack (easy) [future: linear, github]
# 2. Research the updates to understand context
# 3. Fetch images from slack (N/A)
# 4. Draft PR using our brand guidelines and changelog format
# 5. Review the PR to match our tone
# 6. Review the PR to check for devex errors, etc.


async def main():

    options = ClaudeAgentOptions(
        agents={
            "review_and_feedback": AgentDefinition(
                description="Use this agent to review copy and provide feedback on the PR",
                prompt="""
                    You are an expert developer relations professional focused on editorial review.
                    Given a draft changelog and/or PR, evaluate for clarity, tone, correctness, and developer experience.
                    Provide specific, actionable suggestions and, when appropriate, propose improved wording.
                    Check that: brand voice is consistent, technical claims are accurate, links work and are relative, and entries include necessary context.
                    Return a concise list of recommendations and, if asked, an edited version of the text.
                """,
                model="haiku",
                tools=[
                    "mcp__mintlify__SearchMintlify",
                    "mcp__replit__SearchReplit",
                    "Read(./docs/updates/**)",
                    "Edit(./docs/updates/**)",
                ],
            ),
            "changelog_writer": AgentDefinition(
                description="Fetch updates from slack, summarize them, and add relevant links + context from the replit documentation and web search",
                prompt=f"""
                    You are a changelog writer. Create this week's changelog from Slack updates and related docs.

                    Time window: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}
                    Slack channel ID: {os.getenv('SLACK_CHANNEL_ID')}

                    Requirements:
                    - Use fetch_messages_from_channel tool with channel_id and days_back=7 to fetch messages
                    - Extract product changes, summarize crisply, and group logically
                    - Include the originating Slack message URL (permalink) for each entry as a citation
                    - Create a local file at ./docs/updates/YYYY-MM-DD.md (today's date)
                    - Augment entries with relevant Replit docs links using relative paths (no absolute URLs)
                    - Write directly to ./docs/updates/ (no temp folders)

                    Tools available:
                    - fetch_messages_from_channel: Fetch messages with all media and threads from a Slack channel
                    - SearchReplit: Find relevant documentation links
                    - WebSearch: Search the web for additional context
                """,
                model="sonnet",
                tools=[
                    "mcp__slack__fetch_messages_from_channel",
                    "Read(./docs/updates/**)",
                    "Write(./docs/updates/**)",
                    "Edit(./docs/updates/**)",
                    "mcp__replit__SearchReplit",
                    "WebSearch",
                ],
            ),
            "pr_writer": AgentDefinition(
                description="Draft a PR using our brand guidelines and changelog format",
                prompt=f"""
                    You are responsible for packaging and submitting the changelog via GitHub.

                    Repository: {os.getenv('GITHUB_REPO')}

                    Given the generated file at ./docs/updates/YYYY-MM-DD.md:
                    - Create a new branch for the change
                    - Format the changelog according to the changelog template
                    - Commit the changelog file to the same relative path (./docs/updates/YYYY-MM-DD.md) in replit/replit-docs
                    - Open a PR to the repository using the GitHub MCP server (not the CLI)
                    - Update the docs.json in the github repository with the new changelog

                    Use only the configured GitHub MCP server for all Git actions. Do not clone the repository. Do not use the CLI.

                    <changelog_template>
                    {open('changelog_template.md').read()}
                    </changelog_template>
                """,
                model="haiku",
                tools=[
                    "mcp__github__create_pull_request",
                    "mcp__github__create_branch",
                    "mcp__github__list_branches",
                    "mcp__github__list_commits",
                    "mcp__github__push_files",
                    "mcp__github__update_pull_request",
                    "mcp__mintlify__SearchMintlify",
                    "Read(./docs/updates/**)",
                    "Edit(./docs/updates/**)",
                    "WebSearch",
                ],
            ),
        },
        system_prompt="You are an expert developer relations professional.",
        permission_mode="bypassPermissions",
        model=os.getenv("ORCHESTRATOR_MODEL"),
        cwd="./",
        setting_sources=["local"],
        mcp_servers=MCP_SERVERS,
    )

    async for message in query(
        prompt=PROMPT,
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
        if isinstance(message, SystemMessage):
            print(message.data)
        elif (
            isinstance(message, ResultMessage)
            and message.total_cost_usd
            and message.total_cost_usd > 0
        ):
            print(f"\nCost: ${message.total_cost_usd:.4f}")
        else:
            print(message)
    print()


asyncio.run(main())
