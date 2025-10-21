"""Simple, standalone GitHub tools for Claude Agent SDK."""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

from claude_agent_sdk import tool
from dotenv import load_dotenv
from github import Github
from github.GithubException import GithubException

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is not set")
if not GITHUB_REPO:
    raise ValueError("GITHUB_REPO is not set")

# Initialize GitHub client
github_client = Github(GITHUB_TOKEN)

# Configuration
DOCS_JSON_PATH = "docs/docs.json"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_repo():
    """Get the configured GitHub repository."""
    return github_client.get_repo(GITHUB_REPO)


def create_branch_name(prefix: str = "changelog") -> str:
    """Create a unique branch name with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}/{timestamp}"


def parse_changelog_path(changelog_path: str) -> Optional[Dict[str, str]]:
    """Parse a local changelog path to extract date components.

    Expected format: ./docs/updates/YYYY-MM-DD.md or similar
    Returns dict with year, month, day or None if invalid.
    """
    # Match patterns like YYYY-MM-DD or YYYY/MM/DD
    match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", changelog_path)
    if match:
        return {
            "year": match.group(1),
            "month": match.group(2),
            "day": match.group(3),
        }
    return None


def format_pr_body(date_str: str, changelog_path: str, media_count: int = 0) -> str:
    """Generate the pull request body."""
    return f"""🤖 This is an auto-generated pull request from the Changelog Bot

## Summary
This PR contains an automated changelog for:
**{date_str}**

## Changes
- Added new changelog file: `{changelog_path}`
{f'- Added {media_count} media files' if media_count > 0 else ''}
- Updated docs.json with new changelog entry
- Changelog generated using Claude 3.5 Sonnet

## Review Guidelines
Please check:
- [ ] Content accuracy and completeness
- [ ] Formatting and structure (follows changelog template)
- [ ] Links and references are valid
- [ ] Media files are correctly referenced
- [ ] Sensitive information exposure
- [ ] Brand voice and tone consistency

## Note
This PR is created as a draft to allow for human review before publishing.

/label bot
/label automated-pr
/label needs-review
/label changelog
"""


def update_docs_json_content(docs_content: str, year: str, month: str, day: str) -> str:
    """Update docs.json content with new changelog entry.

    Args:
        docs_content: Current docs.json content as string
        year, month, day: Date components for the new changelog

    Returns:
        Updated docs.json content as string
    """
    docs_data = json.loads(docs_content)

    # Create new changelog entry path
    new_entry = f"updates/{year}/{month}/{day}/changelog"

    # For now, we'll create a simple structure
    # In production, you might want to scan existing changelogs
    all_changelogs = [
        {
            "year": year,
            "month": month,
            "day": day,
            "path": new_entry,
        }
    ]

    # Sort changelogs by date (newest first)
    all_changelogs.sort(
        key=lambda x: (
            -int(x["year"]),
            -int(x["month"]),
            -int(x["day"]),
        )
    )

    # Group changelogs by month and year
    grouped_changelogs = {}
    for cl in all_changelogs:
        month_name = datetime.strptime(cl["month"], "%m").strftime("%B")
        group_key = f"{month_name} {cl['year']}"
        if group_key not in grouped_changelogs:
            grouped_changelogs[group_key] = []
        grouped_changelogs[group_key].append(cl["path"])

    # Find the Changelog anchor and update it
    for anchor in docs_data.get("navigation", {}).get("anchors", []):
        if anchor.get("anchor") == "Changelog":
            anchor["icon"] = "clock-rotate-left"
            anchor["description"] = "Latest updates and changes"
            anchor["groups"] = []

            # Add each month group
            for group_name, pages in grouped_changelogs.items():
                anchor["groups"].append({"group": group_name, "pages": pages})
            break

    return json.dumps(docs_data, indent=2)


# ============================================================================
# TOOLS
# ============================================================================


@tool(
    name="create_changelog_pr",
    description="Create a GitHub PR with a changelog file. Handles branch creation, file uploads (changelog + media), docs.json updates, and PR creation. Provide either the local path to the changelog file OR the markdown content directly. Media files should be provided as a list of local file paths.",
    input_schema={
        "type": "object",
        "properties": {
            "changelog_path": {
                "type": "string",
                "description": "Local path to changelog file (e.g., ./docs/updates/2025-01-15.md)",
            },
            "changelog_content": {
                "type": "string",
                "description": "OR provide markdown content directly (optional if changelog_path provided)",
            },
            "media_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of local file paths to media files to upload (optional)",
            },
            "date_override": {
                "type": "string",
                "description": "Override date detection (format: YYYY-MM-DD) (optional)",
            },
            "pr_title": {
                "type": "string",
                "description": "Custom PR title (optional, will be auto-generated if not provided)",
            },
            "draft": {
                "type": "boolean",
                "description": "Create as draft PR (default: True)",
            },
        },
    },
)
async def create_changelog_pr(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a complete changelog PR with all necessary files and updates.

    This tool handles the entire workflow:
    1. Creates a new branch
    2. Reads or receives the changelog content
    3. Uploads media files to appropriate locations
    4. Updates docs.json with the new changelog entry
    5. Creates a pull request

    Returns a dictionary with PR URL and summary for Claude Agent SDK.
    """
    try:
        repo = get_repo()
        default_branch = repo.default_branch

        # Get changelog content
        changelog_path = args.get("changelog_path")
        changelog_content = args.get("changelog_content")

        if not changelog_path and not changelog_content:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: Either changelog_path or changelog_content must be provided",
                    }
                ],
                "is_error": True,
            }

        # Read changelog file if path provided
        if changelog_path and not changelog_content:
            try:
                with open(changelog_path, "r") as f:
                    changelog_content = f.read()
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error reading changelog file: {str(e)}",
                        }
                    ],
                    "is_error": True,
                }

        # Parse date from path or use override
        date_override = args.get("date_override")
        if date_override:
            match = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_override)
            if match:
                date_info = {
                    "year": match.group(1),
                    "month": match.group(2),
                    "day": match.group(3),
                }
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Error: date_override must be in format YYYY-MM-DD",
                        }
                    ],
                    "is_error": True,
                }
        elif changelog_path:
            date_info = parse_changelog_path(changelog_path)
            if not date_info:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Could not parse date from path: {changelog_path}. Use date_override parameter.",
                        }
                    ],
                    "is_error": True,
                }
        else:
            # Use today's date if no path and no override
            today = datetime.now()
            date_info = {
                "year": today.strftime("%Y"),
                "month": today.strftime("%m"),
                "day": today.strftime("%d"),
            }

        year = date_info["year"]
        month = date_info["month"]
        day = date_info["day"]
        date_str = f"{year}-{month}-{day}"

        logger.info(f"Creating changelog PR for date: {date_str}")

        # Create new branch
        branch_name = create_branch_name()
        ref = repo.get_git_ref(f"heads/{default_branch}")
        repo.create_git_ref(f"refs/heads/{branch_name}", ref.object.sha)
        logger.info(f"Created branch: {branch_name}")

        # Track uploaded files
        uploaded_files = []

        # 1. Upload media files if provided
        media_files = args.get("media_files", [])

        # Validate media_files is a list
        if media_files and not isinstance(media_files, list):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: media_files must be a list, got {type(media_files).__name__}. Value: {repr(media_files)}",
                    }
                ],
                "is_error": True,
            }

        media_count = 0
        if media_files:
            logger.info(f"Processing {len(media_files)} media files: {media_files}")
            for local_path in media_files:
                try:
                    # Validate file exists and is a file
                    if not os.path.exists(local_path):
                        logger.error(f"Media file not found: {local_path}")
                        continue

                    if not os.path.isfile(local_path):
                        logger.error(f"Path is not a file: {local_path}")
                        continue

                    with open(local_path, "rb") as f:
                        file_content = f.read()

                    # Determine remote path: images/changelog/YYYY-MM-DD/filename
                    filename = os.path.basename(local_path)
                    remote_path = f"docs/images/changelog/{date_str}/{filename}"

                    repo.create_file(
                        path=remote_path,
                        message=f"Add media file for changelog {date_str}",
                        content=file_content,
                        branch=branch_name,
                    )
                    uploaded_files.append(remote_path)
                    media_count += 1
                    logger.info(f"Uploaded media: {remote_path}")
                except Exception as e:
                    logger.error(f"Error uploading media file {local_path}: {str(e)}")
                    # Continue with other files

        # 2. Create changelog file
        changelog_remote_path = f"docs/updates/{year}/{month}/{day}/changelog.mdx"
        repo.create_file(
            path=changelog_remote_path,
            message=f"Add changelog for {date_str}",
            content=changelog_content,
            branch=branch_name,
        )
        uploaded_files.append(changelog_remote_path)
        logger.info(f"Created changelog: {changelog_remote_path}")

        # 3. Update docs.json
        try:
            docs_file = repo.get_contents(DOCS_JSON_PATH, ref=branch_name)
            current_docs = docs_file.decoded_content.decode()
            updated_docs = update_docs_json_content(current_docs, year, month, day)

            repo.update_file(
                path=DOCS_JSON_PATH,
                message=f"Update docs.json with changelog entry for {date_str}",
                content=updated_docs,
                sha=docs_file.sha,
                branch=branch_name,
            )
            uploaded_files.append(DOCS_JSON_PATH)
            logger.info("Updated docs.json")
        except Exception as e:
            logger.error(f"Error updating docs.json: {str(e)}")
            # Continue to create PR even if docs.json update fails

        # 4. Create pull request
        pr_title = args.get("pr_title") or f"[BOT] Changelog: {date_str}"
        pr_body = format_pr_body(date_str, changelog_remote_path, media_count)
        is_draft = args.get("draft", True)

        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=default_branch,
            draft=is_draft,
        )

        # Add labels
        try:
            pr.add_to_labels("bot", "automated-pr", "needs-review", "changelog")
        except Exception as e:
            logger.warning(f"Could not add labels: {str(e)}")

        # Format success message
        summary = f"✅ Successfully created changelog PR!\n\n"
        summary += f"📅 Date: {date_str}\n"
        summary += f"🌿 Branch: {branch_name}\n"
        summary += f"🔗 PR URL: {pr.html_url}\n"
        summary += f"📝 PR #{pr.number}: {pr_title}\n\n"
        summary += f"📁 Files uploaded ({len(uploaded_files)}):\n"
        for file_path in uploaded_files:
            summary += f"   • {file_path}\n"
        if media_count > 0:
            summary += f"\n📎 Media files: {media_count}\n"
        summary += (
            f"\n{'📄 Draft PR' if is_draft else '✅ Published PR'} - Ready for review!"
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": summary,
                }
            ]
        }

    except GithubException as e:
        error_msg = f"GitHub API Error: {str(e)}"
        logger.error(error_msg)
        return {
            "content": [{"type": "text", "text": error_msg}],
            "is_error": True,
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": [{"type": "text", "text": error_msg}],
            "is_error": True,
        }


@tool(
    name="format_changelog_with_template",
    description="Format changelog content according to the Replit changelog template. Takes raw changelog content and applies proper frontmatter, structure, and formatting.",
    input_schema={
        "raw_content": str,  # Raw changelog content to format
        "date": str,  # Date in format YYYY-MM-DD
        "title_override": str,  # Custom title (optional, will use formatted date if not provided)
    },
)
async def format_changelog_with_template(args: Dict[str, Any]) -> Dict[str, Any]:
    """Format changelog content with proper template structure.

    Returns formatted changelog content ready to be written to file or PR.
    """
    try:
        raw_content = args.get("raw_content")
        date_str = args.get("date")

        if not raw_content or not date_str:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: Both raw_content and date are required",
                    }
                ],
                "is_error": True,
            }

        # Parse date
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")  # e.g., "January 15, 2025"
        except ValueError:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: date must be in format YYYY-MM-DD",
                    }
                ],
                "is_error": True,
            }

        title = args.get("title_override") or formatted_date

        # Build formatted content
        formatted = f"""---
title: {title}
description: 2 min read
---

import {{ AuthorCard }} from '/snippets/author-card.mdx';

<AuthorCard/>

{raw_content}
"""

        summary = f"✅ Formatted changelog for {formatted_date}\n\n"
        summary += f"```markdown\n{formatted[:500]}...\n```\n\n"
        summary += "Ready to create PR or write to file!"

        return {
            "content": [
                {
                    "type": "text",
                    "text": summary,
                },
                {
                    "type": "text",
                    "text": f"\n\nFull formatted content:\n\n{formatted}",
                },
            ]
        }

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "content": [{"type": "text", "text": error_msg}],
            "is_error": True,
        }
