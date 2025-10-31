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
    "add_changelog_frontmatter": "mcp__github_changelog__add_changelog_frontmatter",
    "update_pull_request": "mcp__github__update_pull_request",
    # slack tools
    "fetch_messages_from_channel": "mcp__slack_updates__fetch_messages_from_channel",
}


def get_today_changelog_permissions():
    """Get permissions restricted to today's changelog file only."""
    today = datetime.now().strftime("%Y-%m-%d")
    changelog_file = f"./docs/updates/{today}.md"
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

                    Time window: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}
                    Slack channel ID: {os.getenv('SLACK_CHANNEL_ID')}

                    Requirements:
                    - Use fetch_messages_from_channel tool with channel_id and days_back=7 to fetch messages
                    - Extract product changes, summarize crisply, and group logically
                    - Include the originating Slack message URL (permalink) for each entry as a citation
                    - Create a local file at ./docs/updates/YYYY-MM-DD.md (today's date)
                    - Augment entries with relevant Replit docs links using relative paths (no absolute URLs)
                    - Write directly to ./docs/updates/ (no temp folders)
                    - Focus on content quality, completeness, and accuracy
                    - Don't worry about exact template structure - template_formatter will handle that

                    IMPORTANT - Edit Validation:
                    - Before making any Edit tool call, verify that old_string and new_string are DIFFERENT
                    - Never make an edit where the old and new strings are identical
                    - If content doesn't need changing, skip the edit - don't make a no-op edit
                    - Only make edits that actually change the content

                    Tools available:
                    - fetch_messages_from_channel: Fetch messages with all media and threads from a Slack channel
                    - SearchReplit: Find relevant documentation links
                    - WebSearch: Search the web for additional context

                    <changelog_criteria>
                        {open('./prompts/good_docs.md').read()}
                    </changelog_criteria>

                    <brand_guidelines>
                        {open('./prompts/brand_guidelines.md').read()}
                    </brand_guidelines>

                    <docs_style_guide>
                        {open('./prompts/docs_style_guide.md').read()}
                    </docs_style_guide>

                """,
                model="sonnet",
                tools=permission_groups["changelog_writer"],
            ),
            "template_formatter": AgentDefinition(
                description="Reformat changelog content to match the changelog template structure",
                prompt=f"""
                    You are responsible for reformatting raw changelog content to match the exact template structure.

                    IMPORTANT: You only have permission to access today's changelog file: ./docs/updates/{datetime.now().strftime('%Y-%m-%d')}.md
                    You cannot read or modify older changelog files.

                    Your task:
                    1. Read the raw changelog content from ./docs/updates/{datetime.now().strftime('%Y-%m-%d')}.md (created by changelog_writer)
                    2. Parse the content to identify all updates and their sections
                    3. Categorize each update into "Platform updates" or "Teams and Enterprise" sections:
                       - Teams and Enterprise keywords: Enterprise, Teams, SSO, SAML, SCIM, Identity, Access Management, Viewer Seats, Groups, Permissions, SAML SSO, SCIM provisioning
                       - Everything else → Platform updates
                    4. Extract update titles from ### Update Name headers
                    5. Create bullet point summary lists at the top of each section (e.g., * [Update Name])
                    6. Convert media paths from ./media/YYYY-MM-DD/filename to /images/changelog/YYYY-MM-DD/filename
                    7. Format media files correctly:
                       - Image files (.png, .jpg, .jpeg, .gif, .webp): Wrap in <Frame> with <img> tag: <Frame><img src="..." alt="..." /></Frame>
                       - Video files (.mp4, .mov, .webm): Wrap in <Frame> with <video> tag: <Frame><video src="..." controls /></Frame>
                       - NEVER use <img> tags for video files - always use <video> tags with controls attribute
                    8. Structure content: bullet lists at top, detailed subsections below with ### [Update Name]
                    9. Use the add_changelog_frontmatter tool to add properly formatted frontmatter (with correct single curly braces for AuthorCard import)
                    10. Write the formatted content (with frontmatter) back to the same file path

                    Required structure:
                    - Section headers: "## Platform updates" and "## Teams and Enterprise"
                    - Bullet summaries at top: * [Update Name] for each update in the section
                    - Detailed sections below: ### [Update Name] followed by full content
                    - Media paths: /images/changelog/YYYY-MM-DD/filename (not ./media/...)
                    - ALL images MUST be wrapped in <Frame> components: <Frame><img src="..." alt="..." /></Frame>
                    - ALL videos MUST be wrapped in <Frame> components with <video> tags: <Frame><video src="..." controls /></Frame>
                    - Videos use <video> tag (not <img> tag) - check file extension to determine correct tag type
                    - Frontmatter MUST be added using the add_changelog_frontmatter tool (ensures correct single curly braces format)

                    Before writing, validate:
                    - All updates are properly categorized
                    - Bullet lists match detailed sections
                    - Media paths are converted correctly
                    - ALL images are wrapped in <Frame> components (check every <img> tag)
                    - ALL videos use <video> tags (not <img> tags) and are wrapped in <Frame> components
                    - Video files (.mp4, .mov, .webm) must use <video src="..." controls /> not <img>
                    - Frontmatter was added using the tool (ensures proper format)
                    - Content structure matches template exactly

                    IMPORTANT - Edit Validation:
                    - Before making any Edit tool call, verify that old_string and new_string are DIFFERENT
                    - Never make an edit where the old and new strings are identical
                    - If a section already matches the template, don't try to "fix" it with a no-op edit
                    - Only make edits that actually change the content
                    - Validate that your old_string matches the current file content exactly (including whitespace and newlines)

                    IMPORTANT: Always use the add_changelog_frontmatter tool to add frontmatter. Do not manually write frontmatter. The tool ensures correct formatting with single curly braces for the AuthorCard import (not double braces).

                    Media formatting requirements:
                    - ALL images must be wrapped in <Frame> components
                      - Convert any markdown image syntax (![...]) to: <Frame><img src="..." alt="..." /></Frame>
                      - Convert any standalone <img> tags to: <Frame><img src="..." alt="..." /></Frame>
                    - ALL video files (.mp4, .mov, etc.) must be wrapped in <Frame> components and use <video> tags
                      - Convert any <img src="...*.mp4"> to: <Frame><video src="..." controls /></Frame>
                      - Video files should use <video> tags with controls attribute, NOT <img> tags
                    - Frame component is available by default in Mintlify (no import needed)
                    - File extensions determine the tag type: .png, .jpg, .jpeg, .gif, .webp → <img>, .mp4, .mov, .webm → <video>

                    Important: When reformatting, preserve the brand voice, writing style, and content quality. Maintain consistency with brand guidelines and docs style guide throughout the restructuring process.

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
                model="sonnet",
                tools=permission_groups["template_formatter"],
            ),
            "review_and_feedback": AgentDefinition(
                description="Use this agent to review copy and provide feedback on the PR",
                prompt=f"""
                    You are an expert developer relations professional focused on editorial review.
                    Given a draft changelog and/or PR, evaluate for clarity, tone, correctness, and developer experience.
                    Provide specific, actionable suggestions and, when appropriate, propose improved wording.
                    Check that: brand voice is consistent, technical claims are accurate, links work and are relative, and entries include necessary context.
                    Return a concise list of recommendations and, if asked, an edited version of the text.
                    Assume all details are correct and start work.

                    IMPORTANT - Edit Validation:
                    - Before making any Edit tool call, verify that old_string and new_string are DIFFERENT
                    - Never make an edit where the old and new strings are identical
                    - If content doesn't need changing, skip the edit - don't make a no-op edit
                    - Only make edits that actually change the content
                    - Validate that your old_string matches the current file content exactly

                    Review checklist:
                    - Brand voice and tone consistency (see brand_guidelines)
                    - Documentation style adherence (see docs_style_guide)
                    - Content quality and clarity (see good_docs)
                    - Template structure compliance (see changelog_template)
                    - Technical accuracy and completeness
                    - Link formatting and validity

                    <brand_guidelines>
                        {open('./prompts/brand_guidelines.md').read()}
                    </brand_guidelines>

                    <docs_style_guide>
                        {open('./prompts/docs_style_guide.md').read()}
                    </docs_style_guide>

                    <changelog_criteria>
                        {open('./prompts/good_docs.md').read()}
                    </changelog_criteria>

                    <changelog_template>
                        {open('./prompts/changelog_template.md').read()}
                    </changelog_template>
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
                    You are responsible for packaging and submitting the changelog via GitHub.

                    Repository: {os.getenv('GITHUB_REPO')}

                    Given the formatted changelog file at ./docs/updates/YYYY-MM-DD.md (already formatted by template_formatter):
                    Use create_changelog_pr to create the complete PR with:
                       - The formatted changelog content (or path to the local file, e.g., ./docs/updates/YYYY-MM-DD.md)
                       - DO NOT manually specify media_files parameter - the tool automatically discovers all files in ./docs/updates/media/YYYY-MM-DD/
                       - Even though you have read access to the media directory, you don't need to enumerate or pass those files - let the tool handle discovery
                       - The tool will automatically handle branch creation, file uploads, docs.json updates, and PR creation

                    The create_changelog_pr tool is deterministic and handles the entire workflow:
                    - Creates a new branch
                    - Uploads the changelog file to docs/updates/YYYY/MM/DD/changelog.mdx
                    - Automatically discovers and uploads ALL media files from ./docs/updates/media/YYYY-MM-DD/ to docs/images/changelog/YYYY-MM-DD/
                    - Updates docs.json with the new changelog entry
                    - Creates a draft PR with proper formatting

                    IMPORTANT: Do not pass the media_files parameter. The tool will automatically find and upload all media files in the directory.
                    The changelog should already be properly formatted with frontmatter and template structure by template_formatter, and reviewed by review_and_feedback.
                    You don't need to format or review it - just create the PR with the existing formatted and reviewed content.

                    Do not use the CLI. Use only the configured github_changelog tools.
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
