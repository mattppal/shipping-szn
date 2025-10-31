"""Simple, standalone GitHub tools for Claude Agent SDK."""

import asyncio
import base64
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


async def create_commit_with_files(
    repo,
    branch_name: str,
    files: Dict[str, bytes],
    commit_message: str,
    parent_commit_sha: str,
) -> Optional[str]:
    """Create a single commit with multiple files using Git Data API.

    Args:
        repo: GitHub repository object
        branch_name: Target branch name
        files: Dictionary mapping file paths to file content (bytes)
        commit_message: Commit message
        parent_commit_sha: SHA of the parent commit

    Returns:
        Commit SHA if successful, None otherwise
    """
    try:
        loop = asyncio.get_event_loop()

        def create_commit():
            # Step 1: Create blobs for all files
            blob_shas = {}
            for file_path, file_content in files.items():
                try:
                    # PyGithub create_git_blob expects base64-encoded string
                    # file_content is bytes, so encode to base64 string
                    content_base64 = base64.b64encode(file_content).decode("utf-8")
                    blob = repo.create_git_blob(content_base64, "base64")
                    blob_shas[file_path] = blob.sha
                    logger.info(f"Created blob for: {file_path}")
                except Exception as e:
                    logger.error(f"Error creating blob for {file_path}: {str(e)}")
                    return None

            # Step 2: Get the current tree from parent commit
            parent_commit = repo.get_git_commit(parent_commit_sha)
            base_tree = repo.get_git_tree(parent_commit.tree.sha, recursive=True)

            # Step 3: Create tree entries - preserve existing tree and add/update our files
            tree_entries = []

            # Track which paths we're adding/updating
            paths_to_update = set(blob_shas.keys())

            # Add all existing tree entries that we're not modifying
            for element in base_tree.tree:
                # Only preserve entries that aren't being replaced
                if element.path not in paths_to_update:
                    tree_entries.append(
                        {
                            "path": element.path,
                            "mode": element.mode,
                            "type": element.type,
                            "sha": element.sha,
                        }
                    )

            # Add our new/updated files
            for file_path, blob_sha in blob_shas.items():
                tree_entries.append(
                    {
                        "path": file_path,
                        "mode": "100644",  # Regular file mode
                        "type": "blob",
                        "sha": blob_sha,
                    }
                )

            # Step 4: Create the new tree
            new_tree = repo.create_git_tree(tree_entries)
            logger.info(f"Created tree with {len(tree_entries)} entries")

            # Step 5: Create the commit
            commit = repo.create_git_commit(
                message=commit_message,
                tree=new_tree,
                parents=[parent_commit],
            )
            logger.info(f"Created commit: {commit.sha}")

            return commit.sha

        commit_sha = await loop.run_in_executor(None, create_commit)

        if commit_sha:
            # Step 6: Update the branch reference
            ref = repo.get_git_ref(f"heads/{branch_name}")
            ref.edit(commit_sha)
            logger.info(f"Updated branch {branch_name} to commit {commit_sha}")

        return commit_sha

    except Exception as e:
        logger.error(f"Error creating commit with files: {str(e)}", exc_info=True)
        return None


async def upload_media_file(
    repo, local_path: str, date_str: str, branch_name: str
) -> Optional[str]:
    """Upload a single media file to the repository.

    Handles both creating new files and updating existing files on GitHub.

    Args:
        repo: GitHub repository object
        local_path: Local file path to upload
        date_str: Date string in format YYYY-MM-DD
        branch_name: Target branch name

    Returns:
        Remote path if successful, None otherwise
    """
    try:
        # Validate file exists and is a file
        if not os.path.exists(local_path):
            logger.error(f"Media file not found: {local_path}")
            return None

        if not os.path.isfile(local_path):
            logger.error(f"Path is not a file: {local_path}")
            return None

        with open(local_path, "rb") as f:
            file_content = f.read()

        # Determine remote path: images/changelog/YYYY-MM-DD/filename
        filename = os.path.basename(local_path)
        remote_path = f"docs/images/changelog/{date_str}/{filename}"

        # GitHub API calls are synchronous, so we run them in an executor
        # to avoid blocking the event loop
        loop = asyncio.get_event_loop()

        # Check if file already exists on the branch and upload/update
        def upload_or_update():
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Try to get existing file to check if it exists
                    existing_file = repo.get_contents(remote_path, ref=branch_name)
                    # File exists - check if content is the same
                    existing_content = existing_file.decoded_content
                    if existing_content == file_content:
                        logger.info(f"Media file unchanged, skipping: {remote_path}")
                        return
                    # Content differs - update it with fresh SHA
                    repo.update_file(
                        path=remote_path,
                        message=f"Update media file for changelog {date_str}",
                        content=file_content,
                        sha=existing_file.sha,
                        branch=branch_name,
                    )
                    logger.info(f"Updated existing media: {remote_path}")
                    return
                except GithubException as e:
                    if e.status == 404:
                        # File doesn't exist - create it
                        try:
                            repo.create_file(
                                path=remote_path,
                                message=f"Add media file for changelog {date_str}",
                                content=file_content,
                                branch=branch_name,
                            )
                            logger.info(f"Created new media: {remote_path}")
                            return
                        except GithubException as create_e:
                            # If create fails with 409, file exists (created concurrently)
                            # Get the existing file and update it instead
                            if create_e.status == 409:
                                try:
                                    existing_file = repo.get_contents(
                                        remote_path, ref=branch_name
                                    )
                                    # Check if content is the same
                                    if existing_file.decoded_content == file_content:
                                        logger.info(
                                            f"Media file unchanged (concurrent create), skipping: {remote_path}"
                                        )
                                        return
                                    # Update with current SHA
                                    repo.update_file(
                                        path=remote_path,
                                        message=f"Update media file for changelog {date_str}",
                                        content=file_content,
                                        sha=existing_file.sha,
                                        branch=branch_name,
                                    )
                                    logger.info(
                                        f"Updated media (after concurrent create): {remote_path}"
                                    )
                                    return
                                except GithubException as update_e:
                                    # If update also fails with 409, retry
                                    if (
                                        update_e.status == 409
                                        and attempt < max_retries - 1
                                    ):
                                        logger.warning(
                                            f"Concurrent file modification, retrying: {remote_path}"
                                        )
                                        continue
                                    raise
                            raise
                    elif e.status == 409:
                        # SHA mismatch - file was updated concurrently, retry with fresh SHA
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"SHA mismatch (409), retrying with fresh SHA: {remote_path} (attempt {attempt + 1}/{max_retries})"
                            )
                            continue
                        else:
                            logger.error(
                                f"Failed to update after {max_retries} attempts: {remote_path}"
                            )
                            raise
                    else:
                        # Re-raise other GitHub exceptions
                        raise

        await loop.run_in_executor(None, upload_or_update)

        logger.info(f"Uploaded media: {remote_path}")
        return remote_path
    except Exception as e:
        logger.error(f"Error uploading media file {local_path}: {str(e)}")
        return None


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

    # Extract all existing changelog entries from the current docs.json
    all_changelogs = []

    # Find the Changelog anchor and extract existing entries
    changelog_anchor = None
    for anchor in docs_data.get("navigation", {}).get("anchors", []):
        if anchor.get("anchor") == "Changelog":
            changelog_anchor = anchor
            # Parse existing groups and pages
            for group in anchor.get("groups", []):
                for page_entry in group.get("pages", []):
                    # Handle both string paths and object with name/page
                    if isinstance(page_entry, str):
                        page_path = page_entry
                    elif isinstance(page_entry, dict):
                        page_path = page_entry.get("page", "")
                    else:
                        continue

                    # Extract date from path: updates/YYYY/MM/DD/changelog
                    match = re.match(
                        r"updates/(\d{4})/(\d{2})/(\d{2})/changelog", page_path
                    )
                    if match:
                        all_changelogs.append(
                            {
                                "year": match.group(1),
                                "month": match.group(2),
                                "day": match.group(3),
                                "path": page_path,
                            }
                        )
            break

    # Add the new changelog entry
    all_changelogs.append(
        {
            "year": year,
            "month": month,
            "day": day,
            "path": new_entry,
        }
    )

    # Remove duplicates (in case the entry already exists)
    unique_changelogs = []
    seen_paths = set()
    for cl in all_changelogs:
        if cl["path"] not in seen_paths:
            unique_changelogs.append(cl)
            seen_paths.add(cl["path"])

    # Sort changelogs by date (newest first)
    unique_changelogs.sort(
        key=lambda x: (
            -int(x["year"]),
            -int(x["month"]),
            -int(x["day"]),
        )
    )

    # Group changelogs by month and year (maintaining order)
    from collections import OrderedDict

    grouped_changelogs = OrderedDict()
    for cl in unique_changelogs:
        month_name = datetime.strptime(cl["month"], "%m").strftime("%B")
        group_key = f"{month_name} {cl['year']}"
        if group_key not in grouped_changelogs:
            grouped_changelogs[group_key] = []
        grouped_changelogs[group_key].append(cl["path"])

    # Update the Changelog anchor with all entries (existing + new)
    if changelog_anchor:
        changelog_anchor["icon"] = "clock-rotate-left"
        changelog_anchor["description"] = "Latest updates and changes"
        changelog_anchor["groups"] = []

        # Add each month group (maintaining sorted order with newest first)
        for group_name, pages in grouped_changelogs.items():
            changelog_anchor["groups"].append({"group": group_name, "pages": pages})

    return json.dumps(docs_data, indent=2)


# ============================================================================
# TOOLS
# ============================================================================


@tool(
    name="add_changelog_frontmatter",
    description="Add proper frontmatter to changelog content. Takes raw content and a date, returns content with correctly formatted frontmatter including title, description, and AuthorCard import.",
    input_schema={
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Raw changelog content (without frontmatter)",
            },
            "date": {
                "type": "string",
                "description": "Date in format YYYY-MM-DD",
            },
        },
        "required": ["content", "date"],
    },
)
async def add_changelog_frontmatter(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add properly formatted frontmatter to changelog content.

    Returns changelog content with frontmatter ready to be written to file.
    """
    try:
        content = args.get("content", "").strip()
        date_str = args.get("date")

        if not date_str:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: date is required (format: YYYY-MM-DD)",
                    }
                ],
                "is_error": True,
            }

        # Parse and format date
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")  # e.g., "October 30, 2025"
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

        # Build frontmatter with single curly braces (not double)
        frontmatter = f"""---
title: {formatted_date}
description: 2 min read
---

import {{ AuthorCard }} from '/snippets/author-card.mdx';

<AuthorCard/>

"""

        # Combine frontmatter with content
        formatted_content = frontmatter + content

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"✅ Added frontmatter for {formatted_date}\n\n"
                    f"```markdown\n{formatted_content[:300]}...\n```",
                },
                {
                    "type": "text",
                    "text": f"\n\nFull formatted content:\n\n{formatted_content}",
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
                "description": "List of local file paths to media files to upload (optional). If not provided, will automatically discover all files in ./docs/updates/media/YYYY-MM-DD/",
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

        # Collect all files to commit atomically
        files_to_commit: Dict[str, bytes] = {}

        # 1. Collect media files - auto-discover if not provided
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

        # Auto-discover media files if not provided or empty
        if not media_files:
            media_dir = f"./docs/updates/media/{date_str}"
            if os.path.exists(media_dir) and os.path.isdir(media_dir):
                discovered_files = []
                for filename in os.listdir(media_dir):
                    file_path = os.path.join(media_dir, filename)
                    if os.path.isfile(file_path):
                        discovered_files.append(file_path)
                if discovered_files:
                    logger.info(
                        f"Auto-discovered {len(discovered_files)} media files in {media_dir}"
                    )
                    media_files = discovered_files

        media_count = 0
        if media_files:
            logger.info(f"Processing {len(media_files)} media files: {media_files}")

            # Read all media files into memory
            for local_path in media_files:
                try:
                    with open(local_path, "rb") as f:
                        file_content = f.read()
                    filename = os.path.basename(local_path)
                    remote_path = f"docs/images/changelog/{date_str}/{filename}"
                    files_to_commit[remote_path] = file_content
                    media_count += 1
                except Exception as e:
                    logger.error(f"Error reading media file {local_path}: {str(e)}")

        # 2. Add changelog file
        changelog_remote_path = f"docs/updates/{year}/{month}/{day}/changelog.mdx"
        files_to_commit[changelog_remote_path] = changelog_content.encode("utf-8")

        # 3. Update docs.json
        try:
            # Get current docs.json from the base branch (before our branch changes)
            docs_file = repo.get_contents(DOCS_JSON_PATH, ref=default_branch)
            current_docs = docs_file.decoded_content.decode()
            updated_docs = update_docs_json_content(current_docs, year, month, day)
            if updated_docs:
                files_to_commit[DOCS_JSON_PATH] = updated_docs.encode("utf-8")
                logger.info("Prepared docs.json update")
            else:
                logger.warning("update_docs_json_content returned None, skipping")
        except Exception as e:
            logger.error(f"Error preparing docs.json update: {str(e)}")
            # Continue without docs.json if it fails

        # Commit all files atomically in a single commit
        if files_to_commit:
            parent_commit_sha = ref.object.sha
            commit_message = f"Add changelog for {date_str}"

            commit_sha = await create_commit_with_files(
                repo=repo,
                branch_name=branch_name,
                files=files_to_commit,
                commit_message=commit_message,
                parent_commit_sha=parent_commit_sha,
            )

            if not commit_sha:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Error: Failed to create commit with files",
                        }
                    ],
                    "is_error": True,
                }

            logger.info(
                f"Successfully committed {len(files_to_commit)} files in one commit"
            )
            uploaded_files = list(files_to_commit.keys())

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
