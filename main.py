import asyncio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
)
from mcp_servers import MCP_SERVERS

PROMPT = """
    You have access to the following mcp servers:
    
        - github: use this server to open a PR with the update and perform all other github related actions
        - slack: use this server to fetch data from slack
        - mintlify (our docs framework): use this server to research the functionality of the repo itself
        - replit (our product): use this server to research product functionality and fetch links to features. All links should be formatted using relative paths

    You should use the mcp servers to fetch data and take all actions needed to complete the task.

    DO NOT clone the repository (you are working in a virtual environment), but rather create any necessary files locally and use the github mcp server to open the PR with the update.

    DO NOT use github cli, use the github mcp server instead.

    Your goal is to create a changelog for recent updates to our product.

    You will do so by:
        1. Fetching the last 7 days of messages in the #shipping-szn channel
        2. Summarizing the messages into a structured changelog format
        3. Creating a local file ./updates/YYYY-MM-DD.md with the changelog content, 
        reflecting the current date. Do not use temp folders, write to the updates folder in this directory.
        4. For each update, include the slack message URL as a citation to help 
        reviewers understand the context
        5. Using the github mcp server to create a new branch for the changes
        6. Committing the changelog file to the new branch
        7. Opening a PR for the ccc repository on github (mattppal/ccc) with the 
        date in the PR title

    Remember to use the github mcp server to open the PR with the update.
"""


# Steps:
# 1. Fetch updates from slack (easy) [future: linear, github]
# 2. Research the updates to understand context
# 3. Fetch images from slack (N/A)
# 4. Draft PR using our brand guidelines and changelog format
# 5. Review the PR to match our tone
# 6. Review the PR to check for devex errors, etc.

# TODO:
# 1. Define subagents
# 2. Configure permissions


def create_research_agent(options: ClaudeAgentOptions):
    return AgentDefinition(description="", prompt="", tools=[], model="haiku")


def create_mintlify_agent(options: ClaudeAgentOptions):
    return AgentDefinition(description="", prompt="", tools=[], model="haiku")


def create_slack_agent(options: ClaudeAgentOptions):
    return AgentDefinition(description="", prompt="", tools=[], model="sonnet")


def developer_relations_agent(options: ClaudeAgentOptions):
    return AgentDefinition(description="", prompt="", tools=[], model="sonnet")


def review_agent(options: ClaudeAgentOptions):
    return AgentDefinition(description="", prompt="", tools=[], model="opus")


async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert developer relations professional.",
        permission_mode="acceptEdits",
        mcp_servers=MCP_SERVERS,
        model="claude-sonnet-4-5-20250929",
        cwd="./",
        agents=[
            create_research_agent,
            create_mintlify_agent,
            create_slack_agent,
            developer_relations_agent,
            review_agent,
        ],
        setting_sources=["local"],
    )

    async for message in query(
        prompt=PROMPT,
        options=options,
    ):
        print(message)


asyncio.run(main())
