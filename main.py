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
from servers.slack_tools import fetch_messages_from_channel
from servers.github_tools import create_changelog_pr, add_changelog_frontmatter
from util.messages import display_message

load_dotenv()

DEFAULT_DAYS_BACK = 7
CHANGELOG_FILE_PATTERN = "./docs/updates/{date}.md"

# Path conventions for media files:
# - changelog_writer outputs:    ./media/YYYY-MM-DD/filename (relative to changelog)
# - Actual file location:        ./docs/updates/media/YYYY-MM-DD/filename
# - template_formatter converts: /images/changelog/YYYY-MM-DD/filename (CDN path)
# - Final GitHub location:       docs/images/changelog/YYYY-MM-DD/filename


permissions = {
    # read/write/edit/glob docs (excluding media files)
    "read_docs": "Read(./docs/**/*.md)",
    "write_docs": "Write(./docs/**/*.md)",
    "edit_docs": "Edit(./docs/**/*.md)",
    "glob_docs": "Glob(./docs/**/*.md)",
    # search tools
    "web_search": "WebSearch",
    "search_mintlify": "mcp__mintlify__SearchMintlify",
    "search_replit": "mcp__replit__SearchReplit",
    # github tools (native)
    "create_changelog_pr": create_changelog_pr,
    "add_changelog_frontmatter": add_changelog_frontmatter,
    "update_pull_request": "mcp__github__update_pull_request",
    # slack tools (native)
    "fetch_messages_from_channel": fetch_messages_from_channel,
}


def get_today_changelog_permissions() -> list[str]:
    """Get permissions restricted to today's changelog file only."""
    today = datetime.now().strftime("%Y-%m-%d")
    changelog_file = CHANGELOG_FILE_PATTERN.format(date=today)
    return [
        f"Read({changelog_file})",
        f"Write({changelog_file})",
        f"Edit({changelog_file})",
    ]


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
    ],
    "template_formatter": get_today_changelog_permissions()
    + [permissions["add_changelog_frontmatter"]],
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
    1. changelog_writer: fetch updates from Slack and draft the changelog file (raw content)
    2. template_formatter: reformat the changelog to match template structure
    3. review_and_feedback: review copy/tone/accuracy and suggest or apply improvements (after the changelog is formatted)
    4. pr_writer: create a branch, commit the formatted changelog file, and open a GitHub PR

Guidance and constraints:
    - Use configured MCP servers to fetch data and take actions. Do not use external CLIs.
    - Do NOT clone the repository. Create files locally, then use the GitHub MCP server for git + PR actions.

Plan the sequence, route tasks to the appropriate subagent, verify outputs between steps, and finish when the PR is open and ready for review.

Assume subagents have all relevant information required to begin work.
"""


async def main():
    options = ClaudeAgentOptions(
        agents={
            "changelog_writer": AgentDefinition(
                description="Fetch updates from slack, summarize them, and add relevant links + context from the replit documentation and web search",
                prompt=f"""
                    You are a changelog writer. Create this week's changelog from Slack updates and related docs.

                    Time window: {(datetime.now() - timedelta(days=DEFAULT_DAYS_BACK)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}
                    Slack channel ID: {os.getenv('SLACK_CHANNEL_ID')}

                    Process:
                    1. Use fetch_messages_from_channel (channel_id, days_back={DEFAULT_DAYS_BACK}) to fetch Slack messages
                    2. Extract product changes, summarize crisply, group logically
                    3. **IMPORTANT**: Insert media files into content - check the Slack response for processed_files and add image references using `![alt text](./media/YYYY-MM-DD/filename)` format. The template_formatter will verify files exist and convert paths to CDN format.
                    4. Include Slack message permalink for each entry
                    5. Create ./docs/updates/YYYY-MM-DD.md (today's date)
                    6. Add relevant Replit docs links (relative paths only)
                    7. Focus on content quality - template_formatter handles structure
                    
                    Rules: Only read/write .md files. Only make edits that change content.

                    You have access to skills for brand writing, documentation quality, and media insertion. The media-insertion skill shows you exactly how to add images from Slack into the markdown.
                """,
                model="sonnet",
                tools=permission_groups["changelog_writer"],
            ),
            "template_formatter": AgentDefinition(
                description="Reformat changelog content to match the changelog template structure",
                prompt=f"""
                    Reformat changelog content to match the exact template structure.
                    
                    Access: Only ./docs/updates/{datetime.now().strftime('%Y-%m-%d')}.md (today's file only).

                    Process:
                    1. Read ./docs/updates/{datetime.now().strftime('%Y-%m-%d')}.md
                    2. Categorize updates: "Teams and Enterprise" (SSO, SAML, SCIM, Identity, Access Management, Viewer Seats, Groups, Permissions) or "Platform updates"
                    3. Create structure:
                       - Section headers: "## Platform updates" and "## Teams and Enterprise"
                       - Bullet summaries at top: * [Update Name] for each section
                       - Detailed sections: ### [Update Name] with full content below
                    4. **CRITICAL - Handle media properly**:
                       a. Find all markdown image references: `![alt](./media/YYYY-MM-DD/filename)`
                       b. For each reference, verify the file exists at: `./docs/updates/media/YYYY-MM-DD/filename`
                       c. If file EXISTS:
                          - Convert path: `./media/YYYY-MM-DD/filename` → `/images/changelog/YYYY-MM-DD/filename`
                          - Wrap images: `<Frame><img src="/images/changelog/YYYY-MM-DD/file.png" alt="..." /></Frame>`
                          - Wrap videos: `<Frame><video src="/images/changelog/YYYY-MM-DD/file.mp4" controls /></Frame>`
                       d. If file DOES NOT EXIST: Remove the entire image reference line from the markdown
                    5. Use add_changelog_frontmatter tool (don't write frontmatter manually)
                    6. Write formatted content back to same file path
                    
                    Rules: Only edit when content actually changes. Preserve brand voice and style.

                    You have access to the changelog-formatting skill with complete template and style guidelines. Use it for reference.
                """,
                model="sonnet",
                tools=permission_groups["template_formatter"],
            ),
            "review_and_feedback": AgentDefinition(
                description="Use this agent to review copy and provide feedback on the PR",
                prompt="""
                    Review changelog for clarity, tone, correctness, template compliance, and developer experience.

                    **Formatting Checks (CRITICAL):**
                    - Verify frontmatter was generated by tool (title format: "Month DD, YYYY")
                    - Verify no duplicate section headers (especially "## Teams and Enterprise")
                    - Verify bullet lists use `*` consistently (not `-` or `+`)
                    - Verify all media is wrapped in <Frame> tags
                    - Verify media paths use `/images/changelog/YYYY-MM-DD/` format (not ./media/)
                    - Verify no markdown image syntax remains (`![alt](path)` should be converted to <Frame><img>)

                    **Content Checks:**
                    - Brand voice per brand-writing skill
                    - Technical accuracy
                    - Link validity (relative paths only)
                    - Alt text quality (descriptive, not generic like "image" or "screenshot")

                    Provide specific line-by-line corrections if issues found.
                    Rules: Only read/write .md files. Only edit when content changes.

                    You have access to skills for brand writing, documentation quality, and changelog formatting. Use them to guide your review.
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
            "pr_writer": AgentDefinition(
                description="Draft a PR using our brand guidelines and changelog format",
                prompt=f"""
                    Create GitHub PR with the formatted changelog.

                    Use create_changelog_pr with:
                    - changelog_path: ./docs/updates/YYYY-MM-DD.md
                    - Do NOT pass media_files (auto-discovered)
                    
                    The tool handles: branch creation, file uploads, docs.json updates, PR creation.
                    Repository: {os.getenv('GITHUB_REPO')}
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
