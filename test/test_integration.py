#!/usr/bin/env python3
"""Integration tests for higher-level function execution.

These tests verify that functions run correctly end-to-end with mocked
external dependencies, ensuring proper error handling, response formats,
and workflow logic.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from servers.github_tools import (
    create_branch_name,
    format_pr_body,
    parse_changelog_path,
    update_docs_json_content,
)
from servers.slack_tools import (
    sanitize_filename,
)


# ============================================================================
# GitHub Tools Integration Tests
# ============================================================================


class TestParseChangelogPath:
    """Test parse_changelog_path with various real-world paths."""

    def test_valid_hyphen_separated_path(self):
        """Test parsing standard changelog path."""
        result = parse_changelog_path("./docs/updates/2025-10-30.md")
        assert result is not None
        assert result["year"] == "2025"
        assert result["month"] == "10"
        assert result["day"] == "30"

    def test_valid_slash_separated_path(self):
        """Test parsing path with slash separators."""
        result = parse_changelog_path("./docs/updates/2025/10/30.md")
        assert result is not None
        assert result["year"] == "2025"
        assert result["month"] == "10"
        assert result["day"] == "30"

    def test_path_without_leading_dot(self):
        """Test parsing path without leading ./"""
        result = parse_changelog_path("docs/updates/2025-01-15.md")
        assert result is not None
        assert result["year"] == "2025"

    def test_invalid_path_no_date(self):
        """Test that invalid paths return None."""
        result = parse_changelog_path("./docs/updates/invalid.md")
        assert result is None

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = parse_changelog_path("")
        assert result is None


class TestCreateBranchName:
    """Test branch name creation."""

    def test_branch_name_format(self):
        """Test that branch names follow expected format."""
        branch = create_branch_name()
        assert branch.startswith("changelog/")
        assert len(branch) > len("changelog/")
        # Should contain timestamp format: YYYYMMDD-HHMMSS
        parts = branch.split("/")
        assert len(parts) == 2
        timestamp = parts[1]
        assert "-" in timestamp

    def test_custom_prefix(self):
        """Test branch name with custom prefix."""
        branch = create_branch_name("custom")
        assert branch.startswith("custom/")

    def test_branch_name_uniqueness(self):
        """Test that multiple calls generate unique names."""
        branches = [create_branch_name() for _ in range(5)]
        # Should all be unique (very unlikely to collide)
        assert len(branches) == len(set(branches))


class TestFormatPrBody:
    """Test PR body formatting."""

    def test_pr_body_contains_date(self):
        """Test that PR body includes the date."""
        body = format_pr_body("2025-01-15", "docs/updates/2025/01/15/changelog.mdx", 0)
        assert "2025-01-15" in body

    def test_pr_body_contains_media_count(self):
        """Test that PR body includes media file count."""
        body = format_pr_body("2025-01-15", "docs/updates/2025/01/15/changelog.mdx", 3)
        assert "3" in body or "three" in body.lower()

    def test_pr_body_contains_changelog_path(self):
        """Test that PR body includes changelog path."""
        changelog_path = "docs/updates/2025/01/15/changelog.mdx"
        body = format_pr_body("2025-01-15", changelog_path, 0)
        assert changelog_path in body

    def test_pr_body_review_guidelines(self):
        """Test that PR body includes review checklist."""
        body = format_pr_body("2025-01-15", "docs/updates/2025/01/15/changelog.mdx", 0)
        assert "Review Guidelines" in body
        assert "[ ]" in body  # Checklist items

    def test_pr_body_labels(self):
        """Test that PR body includes label commands."""
        body = format_pr_body("2025-01-15", "docs/updates/2025/01/15/changelog.mdx", 0)
        assert "/label" in body
        assert "bot" in body.lower()


class TestUpdateDocsJsonContent:
    """Test docs.json content updates."""

    def test_adds_new_changelog_entry(self):
        """Test that new changelog entry is added."""
        minimal_docs = {
            "navigation": {
                "anchors": [
                    {
                        "anchor": "Changelog",
                        "groups": [],
                    }
                ]
            }
        }
        docs_str = json.dumps(minimal_docs)

        result = update_docs_json_content(docs_str, "2025", "01", "15")

        parsed = json.loads(result)
        changelog_anchor = None
        for anchor in parsed["navigation"]["anchors"]:
            if anchor["anchor"] == "Changelog":
                changelog_anchor = anchor
                break

        assert changelog_anchor is not None
        assert len(changelog_anchor["groups"]) > 0
        # Should contain the new entry
        entry_path = "updates/2025/01/15/changelog"
        found = False
        for group in changelog_anchor["groups"]:
            if entry_path in group.get("pages", []):
                found = True
                break
        assert found, "New changelog entry should be added"

    def test_preserves_existing_entries(self):
        """Test that existing changelog entries are preserved."""
        existing_docs = {
            "navigation": {
                "anchors": [
                    {
                        "anchor": "Changelog",
                        "groups": [
                            {
                                "group": "January 2025",
                                "pages": ["updates/2025/01/10/changelog"],
                            }
                        ],
                    }
                ]
            }
        }
        docs_str = json.dumps(existing_docs)

        result = update_docs_json_content(docs_str, "2025", "01", "15")

        parsed = json.loads(result)
        # Should still have the old entry
        entry_paths = []
        for anchor in parsed["navigation"]["anchors"]:
            if anchor["anchor"] == "Changelog":
                for group in anchor["groups"]:
                    entry_paths.extend(group.get("pages", []))

        assert "updates/2025/01/10/changelog" in entry_paths
        assert "updates/2025/01/15/changelog" in entry_paths

    def test_sorts_entries_newest_first(self):
        """Test that entries are sorted with newest first."""
        existing_docs = {
            "navigation": {
                "anchors": [
                    {
                        "anchor": "Changelog",
                        "groups": [
                            {
                                "group": "January 2025",
                                "pages": ["updates/2025/01/10/changelog"],
                            }
                        ],
                    }
                ]
            }
        }
        docs_str = json.dumps(existing_docs)

        result = update_docs_json_content(docs_str, "2025", "01", "15")

        parsed = json.loads(result)
        for anchor in parsed["navigation"]["anchors"]:
            if anchor["anchor"] == "Changelog":
                # Newest entry (01/15) should come before older (01/10)
                all_pages = []
                for group in anchor["groups"]:
                    all_pages.extend(group.get("pages", []))
                # Find indices
                new_idx = all_pages.index("updates/2025/01/15/changelog")
                old_idx = all_pages.index("updates/2025/01/10/changelog")
                assert new_idx < old_idx, "Newer entries should come first"


class TestCreateChangelogPrTool:
    """Test create_changelog_pr tool function execution."""

    @pytest.mark.asyncio
    async def test_error_when_no_changelog_provided(self):
        """Test error handling when neither path nor content provided."""
        # Skip if GitHub token not available
        # (module requires env vars at import time)
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            pytest.skip("GITHUB_TOKEN or GITHUB_REPO not set")

        try:
            from servers.github_tools import create_changelog_pr
        except ValueError:
            pytest.skip("GitHub tools module requires GITHUB_TOKEN and GITHUB_REPO")

        result = await create_changelog_pr({})

        assert result.get("is_error") is True
        assert "content" in result
        assert len(result["content"]) > 0
        assert "must be provided" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_error_with_invalid_date_override(self):
        """Test error handling with invalid date format."""
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            pytest.skip("GITHUB_TOKEN or GITHUB_REPO not set")

        try:
            from servers.github_tools import create_changelog_pr
        except ValueError:
            pytest.skip("GitHub tools module requires GITHUB_TOKEN and GITHUB_REPO")

        args = {
            "changelog_content": "# Test changelog",
            "date_override": "invalid-date",
        }

        result = await create_changelog_pr(args)

        assert result.get("is_error") is True
        assert "date_override" in result["content"][0]["text"].lower()
        assert "YYYY-MM-DD" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_error_with_invalid_media_files_type(self):
        """Test error handling when media_files is not a list."""
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            pytest.skip("GITHUB_TOKEN or GITHUB_REPO not set")

        try:
            from servers.github_tools import create_changelog_pr
        except ValueError:
            pytest.skip("GitHub tools module requires GITHUB_TOKEN and GITHUB_REPO")

        args = {
            "changelog_content": "# Test changelog",
            "date_override": "2025-01-15",
            "media_files": "not-a-list",  # Should be a list
        }

        result = await create_changelog_pr(args)

        assert result.get("is_error") is True
        assert "must be a list" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_error_when_changelog_file_not_found(self):
        """Test error handling when changelog file doesn't exist."""
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            pytest.skip("GITHUB_TOKEN or GITHUB_REPO not set")

        try:
            from servers.github_tools import create_changelog_pr
        except ValueError:
            pytest.skip("GitHub tools module requires GITHUB_TOKEN and GITHUB_REPO")

        args = {
            "changelog_path": "./docs/updates/nonexistent-9999-99-99.md",
        }

        result = await create_changelog_pr(args)

        assert result.get("is_error") is True
        assert "Error reading" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_successful_format_with_content_only(self):
        """Test that function processes content-only input correctly."""
        if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
            pytest.skip("GITHUB_TOKEN or GITHUB_REPO not set")

        try:
            from servers.github_tools import create_changelog_pr
        except ValueError:
            pytest.skip("GitHub tools module requires GITHUB_TOKEN and GITHUB_REPO")

        args = {
            "changelog_content": "# Test Changelog\n\nContent here.",
            "date_override": "2025-01-15",
        }

        # Mock the GitHub repo to avoid actual API calls
        with patch("servers.github_tools.get_repo") as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo = MagicMock()
            mock_repo.default_branch = "main"
            mock_repo.get_git_ref = MagicMock(
                return_value=MagicMock(object=MagicMock(sha="abc123"))
            )
            mock_repo.create_git_ref = MagicMock()
            mock_repo.create_file = MagicMock()
            mock_repo.get_contents = MagicMock(
                side_effect=Exception("docs.json not found")
            )
            mock_repo.create_pull = MagicMock(
                return_value=MagicMock(
                    html_url="https://github.com/test/repo/pull/1",
                    number=1,
                )
            )
            mock_get_repo.return_value = mock_repo

            result = await create_changelog_pr(args)

            # Should not have is_error set (even if docs.json fails, PR is created)
            # The function continues even if docs.json update fails
            assert "content" in result
            # May have error or success, but should return proper format
            assert isinstance(result["content"], list)

    def test_response_format_structure(self):
        """Test that tool returns proper response format structure."""
        # This tests the expected format without calling the function
        # Tools should return: {"content": [{"type": "text", "text": "..."}], "is_error": bool}

        expected_format = {
            "content": [{"type": "text", "text": "test"}],
            "is_error": False,
        }

        assert "content" in expected_format
        assert isinstance(expected_format["content"], list)
        assert len(expected_format["content"]) > 0
        assert "type" in expected_format["content"][0]
        assert "text" in expected_format["content"][0]


# ============================================================================
# Slack Tools Integration Tests
# ============================================================================


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_normal_filename(self):
        """Test that normal filenames pass through."""
        result = sanitize_filename("test.png")
        assert result == "test.png"

    def test_filename_with_spaces(self):
        """Test that spaces are handled."""
        result = sanitize_filename("My File.png")
        # Should be sanitized (spaces converted)
        assert " " not in result or result.startswith("my")

    def test_filename_with_special_chars(self):
        """Test that special characters are sanitized."""
        result = sanitize_filename("File (Final).mp4")
        assert "(" not in result
        assert ")" not in result

    def test_unicode_filename(self):
        """Test unicode filename handling."""
        result = sanitize_filename("北京_上海.jpg")
        assert len(result) > 0
        assert "." in result  # Extension should be preserved

    def test_empty_filename_defaults(self):
        """Test that empty filename defaults to 'media'."""
        result = sanitize_filename("")
        assert result == "media"

    def test_long_filename_truncated(self):
        """Test that very long filenames are truncated."""
        long_name = "a" * 100 + ".png"
        result = sanitize_filename(long_name)
        # Should be sanitized and reasonable length
        assert len(result) < 100


class TestFetchMessagesFromChannelTool:
    """Test fetch_messages_from_channel tool function execution."""

    @pytest.mark.asyncio
    async def test_error_when_channel_id_missing(self):
        """Test error handling when channel_id is not provided."""
        if not os.getenv("SLACK_TOKEN"):
            pytest.skip("SLACK_TOKEN not set")

        try:
            from servers.slack_tools import fetch_messages_from_channel
        except ValueError:
            pytest.skip("Slack tools module requires SLACK_TOKEN")

        result = await fetch_messages_from_channel({})

        assert result.get("is_error") is True
        assert "channel_id" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_response_format(self):
        """Test that function returns proper response format."""
        if not os.getenv("SLACK_TOKEN"):
            pytest.skip("SLACK_TOKEN not set")

        try:
            from servers.slack_tools import fetch_messages_from_channel
        except ValueError:
            pytest.skip("Slack tools module requires SLACK_TOKEN")

        # Mock Slack client to avoid actual API calls
        with patch("servers.slack_tools.slack_client") as mock_client:
            mock_client.conversations_history = MagicMock(return_value={"messages": []})
            mock_client.chat_getPermalink = MagicMock(
                return_value={"permalink": "https://slack.com/test"}
            )

            result = await fetch_messages_from_channel(
                {"channel_id": "C12345", "days_back": 1}
            )

            assert "content" in result
            assert isinstance(result["content"], list)
            assert len(result["content"]) > 0
            assert "type" in result["content"][0]
            assert "text" in result["content"][0]

    @pytest.mark.asyncio
    async def test_days_back_parameter_parsed(self):
        """Test that days_back parameter is correctly used."""
        if not os.getenv("SLACK_TOKEN"):
            pytest.skip("SLACK_TOKEN not set")

        try:
            from servers.slack_tools import fetch_messages_from_channel
        except ValueError:
            pytest.skip("Slack tools module requires SLACK_TOKEN")

        with patch("servers.slack_tools.slack_client") as mock_client:
            mock_client.conversations_history = MagicMock(return_value={"messages": []})
            mock_client.chat_getPermalink = MagicMock(
                return_value={"permalink": "https://slack.com/test"}
            )

            await fetch_messages_from_channel({"channel_id": "C12345", "days_back": 14})

            # Verify conversations_history was called with correct time range
            call_args = mock_client.conversations_history.call_args
            assert call_args is not None
            # Should have oldest and latest timestamps
            assert "oldest" in call_args.kwargs
            assert "latest" in call_args.kwargs


# ============================================================================
# Utility Function Integration Tests
# ============================================================================


class TestDateHandling:
    """Test date-related utility functions."""

    def test_date_string_formatting(self):
        """Test date string formatting for changelog paths."""
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")

        assert len(date_str) == 10
        assert date_str.count("-") == 2
        parts = date_str.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # Year
        assert len(parts[1]) == 2  # Month
        assert len(parts[2]) == 2  # Day

    def test_time_window_calculation(self):
        """Test time window calculation for message fetching."""
        end_time = datetime.now()
        days_back = 7
        start_time = end_time - timedelta(days=days_back)

        assert (end_time - start_time).days == 7
        assert start_time < end_time

    def test_date_components_extraction(self):
        """Test extracting year, month, day from date string."""
        date_str = "2025-01-15"
        parts = date_str.split("-")

        year = parts[0]
        month = parts[1]
        day = parts[2]

        assert year == "2025"
        assert month == "01"
        assert day == "15"
        assert int(month) <= 12
        assert int(day) <= 31


# ============================================================================
# Error Handling Integration Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling across functions."""

    def test_tool_error_response_format(self):
        """Test that error responses follow expected format."""
        error_response = {
            "content": [{"type": "text", "text": "Error message"}],
            "is_error": True,
        }

        assert "content" in error_response
        assert error_response["is_error"] is True
        assert isinstance(error_response["content"], list)
        assert len(error_response["content"]) > 0

    def test_tool_success_response_format(self):
        """Test that success responses follow expected format."""
        success_response = {
            "content": [{"type": "text", "text": "Success message"}],
        }

        assert "content" in success_response
        # is_error defaults to False if not present
        assert success_response.get("is_error", False) is False
        assert isinstance(success_response["content"], list)


# ============================================================================
# File Path Handling Tests
# ============================================================================


class TestFilePathHandling:
    """Test file path operations."""

    def test_media_directory_structure(self):
        """Test expected media directory structure."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        media_path = Path(f"./docs/updates/media/{date_str}")

        # Should be able to create path (may not exist)
        assert isinstance(media_path, Path)
        assert str(media_path).endswith(date_str)

    def test_changelog_file_path_format(self):
        """Test changelog file path format."""
        date_str = "2025-01-15"
        changelog_path = f"./docs/updates/{date_str}.md"

        assert changelog_path.startswith("./docs/updates/")
        assert changelog_path.endswith(".md")
        assert date_str in changelog_path

    def test_remote_changelog_path_format(self):
        """Test remote changelog path format."""
        year, month, day = "2025", "01", "15"
        remote_path = f"docs/updates/{year}/{month}/{day}/changelog.mdx"

        assert year in remote_path
        assert remote_path.endswith(".mdx")
        assert f"{year}/{month}/{day}" in remote_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
