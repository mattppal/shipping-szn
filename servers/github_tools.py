"""Simple, standalone GitHub tools for Claude Agent SDK."""

import asyncio
import base64
import json
import logging
import os
import re
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from github import Github
from github.GitTree import GitTree
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

DOCS_JSON_PATH = "docs/docs.json"
CHANGELOG_ANCHOR_NAME = "Changelog"
CHANGELOG_ICON = "clock-rotate-left"
FILE_MODE_REGULAR = "100644"
MAX_RETRIES = 3


def _error_response(message: str) -> Dict[str, Any]:
    """Create standardized error response format."""
    return {
        "content": [{"type": "text", "text": message}],
        "is_error": True,
    }


def _parse_date_from_args(
    args: Dict[str, Any], changelog_path: Optional[str]
) -> Dict[str, str]:
    """Parse date from args or changelog path."""
    date_override = args.get("date_override")
    if date_override:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_override)
        if match:
            return {
                "year": match.group(1),
                "month": match.group(2),
                "day": match.group(3),
            }
        else:
            raise ValueError("date_override must be in format YYYY-MM-DD")
    elif changelog_path:
        date_info = parse_changelog_path(changelog_path)
        if not date_info:
            raise ValueError(
                f"Could not parse date from path: {changelog_path}. Use date_override parameter."
            )
        return date_info
    else:
        today = datetime.now()
        return {
            "year": today.strftime("%Y"),
            "month": today.strftime("%m"),
            "day": today.strftime("%d"),
        }


def _discover_media_files(date_str: str, referenced_filenames: set) -> list[str]:
    """Discover media files in the media directory."""
    media_dir = f"./docs/updates/media/{date_str}"
    discovered_files = []
    if os.path.exists(media_dir) and os.path.isdir(media_dir):
        for filename in os.listdir(media_dir):
            file_path = os.path.join(media_dir, filename)
            if os.path.isfile(file_path):
                discovered_files.append(file_path)

    if referenced_filenames:
        found_filenames = {os.path.basename(f) for f in discovered_files}
        missing_refs = referenced_filenames - found_filenames

        if missing_refs:
            media_base = "./docs/updates/media"
            if os.path.exists(media_base):
                for date_dir in os.listdir(media_base):
                    date_dir_path = os.path.join(media_base, date_dir)
                    if os.path.isdir(date_dir_path):
                        for filename in os.listdir(date_dir_path):
                            if filename in missing_refs:
                                file_path = os.path.join(date_dir_path, filename)
                                if os.path.isfile(file_path):
                                    discovered_files.append(file_path)

    return discovered_files


def _validate_media_references(
    referenced_filenames: set, found_referenced_files: set
) -> Optional[str]:
    """Validate that all referenced media files exist."""
    if referenced_filenames:
        missing_files = referenced_filenames - found_referenced_files
        if missing_files:
            missing_list = ", ".join(sorted(missing_files)[:5])
            if len(missing_files) > 5:
                missing_list += f" and {len(missing_files) - 5} more"
            return (
                f"Error: Changelog references {len(missing_files)} media files "
                f"that don't exist locally: {missing_list}. "
                f"Please ensure all referenced media files are downloaded "
                f"before creating the PR."
            )
    return None


def _group_changelogs_by_month(
    unique_changelogs: list[Dict[str, str]],
) -> OrderedDict[str, list[str]]:
    """Group changelogs by month and year."""
    grouped_changelogs: OrderedDict[str, list[str]] = OrderedDict()
    for cl in unique_changelogs:
        month_name = datetime.strptime(cl["month"], "%m").strftime("%B")
        group_key = f"{month_name} {cl['year']}"
        if group_key not in grouped_changelogs:
            grouped_changelogs[group_key] = []
        grouped_changelogs[group_key].append(cl["path"])
    return grouped_changelogs


def create_branch_name(prefix: str = "changelog") -> str:
    """Create a unique branch name with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}/{timestamp}"


def get_repo():
    """Get the configured GitHub repository."""
    return github_client.get_repo(GITHUB_REPO)


def parse_changelog_path(changelog_path: str) -> Optional[Dict[str, str]]:
    """Parse a local changelog path to extract date components.

    Expected format: ./docs/updates/YYYY-MM-DD.md or similar
    Returns dict with year, month, day or None if invalid.
    """
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
    return f"""This is an auto-generated pull request from the Changelog Bot

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
    repo: Any,
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
            blob_shas = {}
            for file_path, file_content in files.items():
                try:
                    content_base64 = base64.b64encode(file_content).decode("utf-8")
                    blob = repo.create_git_blob(content_base64, "base64")
                    blob_shas[file_path] = blob.sha
                except Exception as e:
                    logger.error(f"Error creating blob for {file_path}: {str(e)}")
                    return None

            parent_commit = repo.get_git_commit(parent_commit_sha)
            base_tree_sha = parent_commit.tree.sha

            tree_entries = []
            for file_path, blob_sha in blob_shas.items():
                tree_entries.append(
                    {
                        "path": file_path,
                        "mode": FILE_MODE_REGULAR,
                        "type": "blob",
                        "sha": blob_sha,
                    }
                )

            try:
                tree_data = {
                    "base_tree": base_tree_sha,
                    "tree": tree_entries,
                }
                headers = {"Accept": "application/vnd.github.v3+json"}
                tree_result = repo._requester.requestJsonAndCheck(
                    "POST", f"{repo.url}/git/trees", input=tree_data, headers=headers
                )
                new_tree_sha = tree_result[1]["sha"]

                new_tree = GitTree(
                    repo._requester,
                    repo._headers,
                    {"sha": new_tree_sha},
                    completed=True,
                )
            except Exception as e:
                logger.error(f"Error creating tree: {str(e)}")
                raise

            try:
                commit = repo.create_git_commit(
                    message=commit_message,
                    tree=new_tree,
                    parents=[parent_commit],
                )
                return commit.sha
            except Exception as e:
                logger.error(f"Error creating commit: {str(e)}")
                raise

        commit_sha = await loop.run_in_executor(None, create_commit)

        if commit_sha:
            ref = repo.get_git_ref(f"heads/{branch_name}")
            ref.edit(commit_sha)

        return commit_sha

    except Exception as e:
        logger.error(f"Error creating commit with files: {str(e)}", exc_info=True)
        return None


async def upload_media_file(
    repo: Any, local_path: str, date_str: str, branch_name: str
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
        if not os.path.exists(local_path) or not os.path.isfile(local_path):
            return None

        with open(local_path, "rb") as f:
            file_content = f.read()

        filename = os.path.basename(local_path)
        remote_path = f"docs/images/changelog/{date_str}/{filename}"

        loop = asyncio.get_event_loop()

        def upload_or_update():
            max_retries = MAX_RETRIES
            for attempt in range(max_retries):
                try:
                    existing_file = repo.get_contents(remote_path, ref=branch_name)
                    if existing_file.decoded_content == file_content:
                        return
                    repo.update_file(
                        path=remote_path,
                        message=f"Update media file for changelog {date_str}",
                        content=file_content,
                        sha=existing_file.sha,
                        branch=branch_name,
                    )
                    return
                except GithubException as e:
                    if e.status == 404:
                        try:
                            repo.create_file(
                                path=remote_path,
                                message=f"Add media file for changelog {date_str}",
                                content=file_content,
                                branch=branch_name,
                            )
                            return
                        except GithubException as create_e:
                            if create_e.status == 409:
                                try:
                                    existing_file = repo.get_contents(
                                        remote_path, ref=branch_name
                                    )
                                    if existing_file.decoded_content == file_content:
                                        return
                                    repo.update_file(
                                        path=remote_path,
                                        message=f"Update media file for changelog {date_str}",
                                        content=file_content,
                                        sha=existing_file.sha,
                                        branch=branch_name,
                                    )
                                    return
                                except GithubException as update_e:
                                    if (
                                        update_e.status == 409
                                        and attempt < max_retries - 1
                                    ):
                                        continue
                                    raise
                            raise
                    elif e.status == 409:
                        if attempt < max_retries - 1:
                            continue
                        raise
                    else:
                        raise

        await loop.run_in_executor(None, upload_or_update)
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

    new_entry = f"updates/{year}/{month}/{day}/changelog"

    all_changelogs = []

    changelog_anchor = None
    for anchor in docs_data.get("navigation", {}).get("anchors", []):
        if anchor.get("anchor") == CHANGELOG_ANCHOR_NAME:
            changelog_anchor = anchor
            for group in anchor.get("groups", []):
                for page_entry in group.get("pages", []):
                    if isinstance(page_entry, str):
                        page_path = page_entry
                    elif isinstance(page_entry, dict):
                        page_path = page_entry.get("page", "")
                    else:
                        continue

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

    all_changelogs.append(
        {
            "year": year,
            "month": month,
            "day": day,
            "path": new_entry,
        }
    )

    unique_changelogs = []
    seen_paths = set()
    for cl in all_changelogs:
        if cl["path"] not in seen_paths:
            unique_changelogs.append(cl)
            seen_paths.add(cl["path"])

    unique_changelogs.sort(
        key=lambda x: (
            -int(x["year"]),
            -int(x["month"]),
            -int(x["day"]),
        )
    )

    grouped_changelogs = _group_changelogs_by_month(unique_changelogs)

    if changelog_anchor:
        changelog_anchor["icon"] = CHANGELOG_ICON
        changelog_anchor["description"] = "Latest updates and changes"
        changelog_anchor["groups"] = []

        for group_name, pages in grouped_changelogs.items():
            changelog_anchor["groups"].append({"group": group_name, "pages": pages})

    return json.dumps(docs_data, indent=2)


async def add_changelog_frontmatter(content: str, date: str) -> Dict[str, Any]:
    """Add properly formatted frontmatter to changelog content.

    Args:
        content: Raw changelog content (without frontmatter)
        date: Date in format YYYY-MM-DD

    Returns changelog content with frontmatter ready to be written to file.
    """
    try:
        content = content.strip()
        date_str = date

        if not date_str:
            return _error_response("Error: date is required (format: YYYY-MM-DD)")

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except ValueError:
            return _error_response("Error: date must be in format YYYY-MM-DD")

        frontmatter = f"""---
title: {formatted_date}
description: 2 min read
---

import {{ AuthorCard }} from '/snippets/author-card.mdx';

<AuthorCard/>

"""

        formatted_content = frontmatter + content

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Added frontmatter for {formatted_date}\n\n"
                    f"```markdown\n{formatted_content[:300]}...\n```",
                },
                {
                    "type": "text",
                    "text": f"\n\nFull formatted content:\n\n{formatted_content}",
                },
            ]
        }

    except Exception as e:
        return _error_response(f"Unexpected error: {str(e)}")


async def create_changelog_pr(
    changelog_path: Optional[str] = None,
    changelog_content: Optional[str] = None,
    media_files: Optional[list[str]] = None,
    date_override: Optional[str] = None,
    pr_title: Optional[str] = None,
    draft: bool = True,
) -> Dict[str, Any]:
    """Create a complete changelog PR with all necessary files and updates.

    This tool handles the entire workflow:
    1. Creates a new branch
    2. Reads or receives the changelog content
    3. Uploads media files to appropriate locations
    4. Updates docs.json with the new changelog entry
    5. Creates a pull request

    Args:
        changelog_path: Local path to changelog file (e.g., ./docs/updates/2025-01-15.md)
        changelog_content: OR provide markdown content directly (optional if changelog_path provided)
        media_files: List of local file paths to media files to upload (optional, auto-discovered if not provided)
        date_override: Override date detection (format: YYYY-MM-DD) (optional)
        pr_title: Custom PR title (optional, will be auto-generated if not provided)
        draft: Create as draft PR (default: True)

    Returns a dictionary with PR URL and summary.
    """
    try:
        repo = get_repo()
        default_branch = repo.default_branch

        if not changelog_path and not changelog_content:
            return _error_response(
                "Error: Either changelog_path or changelog_content must be provided"
            )

        if changelog_path and not changelog_content:
            try:
                with open(changelog_path, "r") as f:
                    changelog_content = f.read()
            except Exception as e:
                return _error_response(f"Error reading changelog file: {str(e)}")

        # Build args dict for _parse_date_from_args compatibility
        args = {"date_override": date_override}
        try:
            date_info = _parse_date_from_args(args, changelog_path)
        except ValueError as e:
            return _error_response(f"Error: {str(e)}")

        year = date_info["year"]
        month = date_info["month"]
        day = date_info["day"]
        date_str = f"{year}-{month}-{day}"

        branch_name = create_branch_name()
        ref = repo.get_git_ref(f"heads/{default_branch}")
        repo.create_git_ref(f"refs/heads/{branch_name}", ref.object.sha)

        files_to_commit: Dict[str, bytes] = {}

        referenced_filenames = set()
        if changelog_content:
            date_pattern = date_str.replace("-", r"\-")
            referenced_filenames = set(
                re.findall(
                    rf'/images/changelog/{date_pattern}/([^"\s)]+)',
                    changelog_content,
                )
            )

        if media_files is None:
            media_files = []

        if not isinstance(media_files, list):
            return _error_response(
                f"Error: media_files must be a list, got {type(media_files).__name__}. Value: {repr(media_files)}"
            )

        if not media_files:
            discovered_files = _discover_media_files(date_str, referenced_filenames)
            if discovered_files:
                media_files = discovered_files

        found_referenced_files = set()

        media_count = 0
        if media_files:
            for local_path in media_files:
                try:
                    with open(local_path, "rb") as f:
                        file_content = f.read()
                    filename = os.path.basename(local_path)
                    remote_path = f"docs/images/changelog/{date_str}/{filename}"
                    files_to_commit[remote_path] = file_content
                    media_count += 1
                    if filename in referenced_filenames:
                        found_referenced_files.add(filename)
                except Exception:
                    pass

        validation_error = _validate_media_references(
            referenced_filenames, found_referenced_files
        )
        if validation_error:
            return _error_response(validation_error)

        if not changelog_content:
            return _error_response("Error: Changelog content is empty")
        changelog_remote_path = f"docs/updates/{year}/{month}/{day}/changelog.mdx"
        files_to_commit[changelog_remote_path] = changelog_content.encode("utf-8")

        try:
            docs_file = repo.get_contents(DOCS_JSON_PATH, ref=default_branch)
            current_docs = docs_file.decoded_content.decode()
            updated_docs = update_docs_json_content(current_docs, year, month, day)
            if updated_docs:
                files_to_commit[DOCS_JSON_PATH] = updated_docs.encode("utf-8")
        except Exception:
            pass

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
                return _error_response("Error: Failed to create commit with files.")

            uploaded_files = list(files_to_commit.keys())

        final_pr_title = pr_title or f"[BOT] Changelog: {date_str}"
        pr_body = format_pr_body(date_str, changelog_remote_path, media_count)
        is_draft = draft

        pr = repo.create_pull(
            title=final_pr_title,
            body=pr_body,
            head=branch_name,
            base=default_branch,
            draft=is_draft,
        )

        try:
            pr.add_to_labels("bot", "automated-pr", "needs-review", "changelog")
        except Exception:
            pass

        uploaded_files = list(files_to_commit.keys())
        summary = "Successfully created changelog PR\n\n"
        summary += f"Date: {date_str}\n"
        summary += f"Branch: {branch_name}\n"
        summary += f"PR URL: {pr.html_url}\n"
        summary += f"PR #{pr.number}: {final_pr_title}\n\n"
        summary += f"Files uploaded ({len(uploaded_files)}):\n"
        for file_path in uploaded_files:
            summary += f"   {file_path}\n"
        if media_count > 0:
            summary += f"\nMedia files: {media_count}\n"
        summary += f"\n{'Draft PR' if is_draft else 'Published PR'} - Ready for review"

        return {
            "content": [
                {
                    "type": "text",
                    "text": summary,
                }
            ]
        }

    except GithubException as e:
        return _error_response(f"GitHub API Error: {str(e)}")
    except Exception as e:
        return _error_response(f"Unexpected error: {str(e)}")
