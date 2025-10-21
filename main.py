import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from claude_agent_sdk import (
    ClaudeAgentOptions,
    AgentDefinition,
    ClaudeSDKClient,
)

from servers.config import MCP_SERVERS
from util.messages import display_message

load_dotenv()


permissions = {
    # read/write/edit/glob docs and media
    "read_docs": "Read(./docs/**/*)",
    "write_docs": "Write(./docs/**/*)",
    "edit_docs": "Edit(./docs/**/*)",
    "glob_docs": "Glob(./docs/**/*)",
    # search tools
    "web_search": "WebSearch",
    "search_mintlify": "mcp__mintlify__SearchMintlify",
    "search_replit": "mcp__replit__SearchReplit",
    # github tools
    "create_changelog_pr": "mcp__github_changelog__create_changelog_pr",
    "update_pull_request": "mcp__github__update_pull_request",
    # slack tools
    "fetch_messages_from_channel": "mcp__slack_updates__fetch_messages_from_channel",
}

permission_groups = {
    "review_and_feedback": [
        permissions["read_docs"],
        permissions["edit_docs"],
        permissions["web_search"],
        permissions["search_mintlify"],
        permissions["search_replit"],
    ],
    "changelog_writer": [
        permissions["fetch_messages_from_channel"],
        permissions["read_docs"],
        permissions["write_docs"],
        permissions["edit_docs"],
        permissions["search_replit"],
        permissions["web_search"],
    ],
    "pr_writer": [
        permissions["create_changelog_pr"],
        permissions["update_pull_request"],
        permissions["search_mintlify"],
        permissions["web_search"],
        permissions["read_docs"],
        permissions["write_docs"],
        permissions["edit_docs"],
        permissions["glob_docs"],
    ],
}


USER_PROMPT = """You are the orchestrator for creating and shipping a product changelog.

Delegate concrete work to subagents and coordinate end-to-end:
    1. changelog_writer: fetch updates from Slack and draft the changelog file
    2. review_and_feedback: review copy/tone/accuracy and suggest or apply improvements (after the changelog is written)
    3. pr_writer: create a branch, commit the changelog file, and open a GitHub PR

Guidance and constraints:
    - Use configured MCP servers to fetch data and take actions. Do not use external CLIs.
    - Do NOT clone the repository. Create files locally, then use the GitHub MCP server for git + PR actions.

Plan the sequence, route tasks to the appropriate subagent, verify outputs between steps, and finish when the PR is open and ready for review.

Assume subagents have all relevant information required to begin work.
"""


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
                    Assume all details are correct and start work.
                """,
                model="haiku",
                tools=[
                    permissions["read_docs"],
                    permissions["edit_docs"],
                    permissions["web_search"],
                    permissions["search_mintlify"],
                    permissions["search_replit"],
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

                    <changelog_criteria>
                        {open('./prompts/good_docs.md').read()}
                    </changelog_criteria>

                """,
                model="sonnet",
                tools=permission_groups["changelog_writer"],
            ),
            "pr_writer": AgentDefinition(
                description="Draft a PR using our brand guidelines and changelog format",
                prompt=f"""
                    You are responsible for packaging and submitting the changelog via GitHub.

                    Repository: {os.getenv('GITHUB_REPO')}

                    Given the generated file at ./docs/updates/YYYY-MM-DD.md:
                    Use create_changelog_pr to create the complete PR with:
                       - The formatted changelog content (or path to the local file)
                       - Any media files from ./docs/updates/media/YYYY-MM-DD/
                       - The tool will automatically handle branch creation, file uploads, docs.json updates, and PR creation

                    The create_changelog_pr tool is deterministic and handles the entire workflow:
                    - Creates a new branch
                    - Uploads the changelog file to docs/updates/YYYY/MM/DD/changelog.mdx
                    - Uploads media files to docs/images/changelog/YYYY-MM-DD/
                    - Updates docs.json with the new changelog entry
                    - Creates a draft PR with proper formatting

                    Do not use the CLI. Use only the configured github_changelog tools.

                    <changelog_template>
                        {open('./prompts/changelog_template.md').read()}
                    </changelog_template>

                    <brand_guidelines>
                        {open('./prompts/brand_guidelines.md').read()}
                    </brand_guidelines>

                    <docs_style_guide>
                        {open('./prompts/docs_style_guide.md').read()}
                    </docs_style_guide>
                """,
                model="haiku",
                tools=permission_groups["pr_writer"],
            ),
        },
        system_prompt="You are an expert developer relations professional.",
        permission_mode="bypassPermissions",
        model=os.getenv("ORCHESTRATOR_MODEL"),
        cwd="./",
        setting_sources=None,
        mcp_servers=MCP_SERVERS,
    )
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt=USER_PROMPT)

        async for message in client.receive_response():
            display_message(message)


asyncio.run(main())
