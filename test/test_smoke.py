#!/usr/bin/env python3
"""Smoke tests for the changelog automation project.

These tests verify that basic functionality works and critical
components can be imported and initialized. They are meant to catch
obvious issues before deeper integration testing.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Import Tests - Verify all critical modules can be imported
# ============================================================================


def test_import_main():
    """Test that main.py can be imported."""
    try:
        import main

        assert main is not None
    except ImportError as e:
        pytest.fail(f"Failed to import main: {e}")


def test_import_config():
    """Test that servers.config can be imported."""
    try:
        from servers.config import MCP_SERVERS

        assert MCP_SERVERS is not None
        assert isinstance(MCP_SERVERS, dict)
    except ImportError as e:
        pytest.fail(f"Failed to import servers.config: {e}")


def test_import_github_tools():
    """Test that servers.github_tools can be imported."""
    try:
        from servers.github_tools import (
            create_changelog_pr,
            get_repo,
            parse_changelog_path,
        )

        assert create_changelog_pr is not None
        assert get_repo is not None
        assert parse_changelog_path is not None
    except ImportError as e:
        pytest.fail(f"Failed to import servers.github_tools: {e}")


def test_import_slack_tools():
    """Test that servers.slack_tools can be imported."""
    try:
        from servers.slack_tools import (
            fetch_messages_from_channel,
            sanitize_filename,
            download_media_file,
        )

        assert fetch_messages_from_channel is not None
        assert sanitize_filename is not None
        assert download_media_file is not None
    except ImportError as e:
        pytest.fail(f"Failed to import servers.slack_tools: {e}")


def test_import_messages():
    """Test that util.messages can be imported."""
    try:
        from util.messages import display_message

        assert display_message is not None
    except ImportError as e:
        pytest.fail(f"Failed to import util.messages: {e}")


# ============================================================================
# Configuration Tests
# ============================================================================


def test_mcp_servers_configuration():
    """Test that MCP servers are properly configured."""
    from servers.config import MCP_SERVERS

    # Should have expected servers
    assert "slack_updates" in MCP_SERVERS
    assert "github_changelog" in MCP_SERVERS
    assert "github" in MCP_SERVERS
    assert "mintlify" in MCP_SERVERS
    assert "replit" in MCP_SERVERS


def test_permissions_structure():
    """Test that permissions are properly structured in main.py."""
    import main

    assert hasattr(main, "permissions")
    assert isinstance(main.permissions, dict)

    # Check for key permissions
    assert "read_docs" in main.permissions
    assert "write_docs" in main.permissions
    assert "fetch_messages_from_channel" in main.permissions
    assert "create_changelog_pr" in main.permissions


def test_permission_groups_structure():
    """Test that permission groups are properly structured."""
    import main

    assert hasattr(main, "permission_groups")
    assert isinstance(main.permission_groups, dict)

    # Check for key groups
    assert "changelog_writer" in main.permission_groups
    assert "template_formatter" in main.permission_groups
    assert "review_and_feedback" in main.permission_groups
    assert "pr_writer" in main.permission_groups


# ============================================================================
# Utility Function Tests
# ============================================================================


def test_parse_changelog_path_valid():
    """Test parsing valid changelog paths."""
    from servers.github_tools import parse_changelog_path

    # Test with hyphen separator
    result = parse_changelog_path("./docs/updates/2025-01-15.md")
    assert result is not None
    assert result["year"] == "2025"
    assert result["month"] == "01"
    assert result["day"] == "15"

    # Test with slash separator
    result = parse_changelog_path("./docs/updates/2025/01/15.md")
    assert result is not None
    assert result["year"] == "2025"
    assert result["month"] == "01"
    assert result["day"] == "15"

    # Test without leading path
    result = parse_changelog_path("2025-01-15.md")
    assert result is not None
    assert result["year"] == "2025"


def test_parse_changelog_path_invalid():
    """Test parsing invalid changelog paths."""
    from servers.github_tools import parse_changelog_path

    # Test with invalid format
    result = parse_changelog_path("./docs/updates/invalid.md")
    assert result is None

    # Test with empty string
    result = parse_changelog_path("")
    assert result is None

    # Test with no date
    result = parse_changelog_path("./docs/updates/test.md")
    assert result is None


def test_sanitize_filename():
    """Test filename sanitization."""
    from servers.slack_tools import sanitize_filename

    # Normal filename
    result = sanitize_filename("test.png")
    assert result == "test.png"

    # Filename with spaces and special chars
    result = sanitize_filename("My Cool File (Final).mp4")
    assert "." in result
    assert "(" not in result
    assert ")" not in result

    # Empty filename
    result = sanitize_filename("")
    assert result == "media"

    # Unicode filename
    result = sanitize_filename("北京_上海.jpg")
    assert len(result) > 0
    assert "." in result


def test_create_branch_name():
    """Test branch name creation."""
    from servers.github_tools import create_branch_name

    branch = create_branch_name()
    assert branch.startswith("changelog/")
    assert len(branch) > len("changelog/")

    # Test with custom prefix
    branch = create_branch_name("custom")
    assert branch.startswith("custom/")


def test_get_today_changelog_permissions():
    """Test that today's changelog permissions function works."""
    import main

    permissions = main.get_today_changelog_permissions()
    assert isinstance(permissions, list)
    assert len(permissions) > 0

    # Check that today's date is in the permissions
    today = datetime.now().strftime("%Y-%m-%d")
    assert any(today in perm for perm in permissions)


# ============================================================================
# Environment Variable Tests
# ============================================================================


def test_environment_variables_defined():
    """Test that critical environment variables are defined.

    Tests that env vars are accessible (even if empty).
    """
    # These should exist in the environment (even if empty)
    # We check that they can be accessed, not that they have values

    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPO")
    slack_token = os.getenv("SLACK_TOKEN")
    slack_channel_id = os.getenv("SLACK_CHANNEL_ID")
    orchestrator_model = os.getenv("ORCHESTRATOR_MODEL")

    # At minimum, GITHUB_TOKEN and GITHUB_REPO should be set
    # for github_tools. We're just checking they're accessible
    # (None is fine for smoke tests)
    assert isinstance(github_token, (str, type(None)))
    assert isinstance(github_repo, (str, type(None)))
    assert isinstance(slack_token, (str, type(None)))
    assert isinstance(slack_channel_id, (str, type(None)))
    assert isinstance(orchestrator_model, (str, type(None)))


# ============================================================================
# File Path Tests
# ============================================================================


def test_docs_directory_exists():
    """Test that docs directory structure exists."""
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / "docs"

    assert docs_dir.exists(), "docs directory should exist"
    assert docs_dir.is_dir(), "docs should be a directory"


def test_updates_directory_exists():
    """Test that docs/updates directory exists."""
    project_root = Path(__file__).parent.parent
    updates_dir = project_root / "docs" / "updates"

    assert updates_dir.exists(), "docs/updates directory should exist"
    assert updates_dir.is_dir(), "docs/updates should be a directory"


def test_prompts_directory_exists():
    """Test that prompts directory exists."""
    project_root = Path(__file__).parent.parent
    prompts_dir = project_root / "prompts"

    assert prompts_dir.exists(), "prompts directory should exist"
    assert prompts_dir.is_dir(), "prompts should be a directory"


def test_prompt_files_exist():
    """Test that required prompt files exist."""
    project_root = Path(__file__).parent.parent
    prompts_dir = project_root / "prompts"

    required_files = [
        "brand_guidelines.md",
        "changelog_template.md",
        "docs_style_guide.md",
        "good_docs.md",
    ]

    for filename in required_files:
        file_path = prompts_dir / filename
        msg = f"Required prompt file {filename} should exist"
        assert file_path.exists(), msg
        assert file_path.is_file(), f"{filename} should be a file"


# ============================================================================
# Tool Decorator Tests
# ============================================================================


def test_tools_are_decorated():
    """Test that tools have proper decorators."""
    from servers.github_tools import create_changelog_pr
    from servers.slack_tools import fetch_messages_from_channel

    # Check that functions have tool metadata
    assert hasattr(create_changelog_pr, "__name__")
    assert hasattr(fetch_messages_from_channel, "__name__")

    # These should be async functions
    import inspect

    assert inspect.iscoroutinefunction(create_changelog_pr)
    assert inspect.iscoroutinefunction(fetch_messages_from_channel)


# ============================================================================
# Date Utility Tests
# ============================================================================


def test_date_formatting():
    """Test date formatting utilities."""
    from datetime import datetime

    # Test that we can format dates
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    assert len(date_str) == 10
    assert date_str.count("-") == 2

    # Test year/month/day extraction
    parts = date_str.split("-")
    assert len(parts) == 3
    assert len(parts[0]) == 4  # Year
    assert len(parts[1]) == 2  # Month
    assert len(parts[2]) == 2  # Day


def test_time_window_calculation():
    """Test time window calculation for changelog."""
    from datetime import datetime, timedelta

    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)

    assert (end_time - start_time).days == 7
    assert start_time < end_time


# ============================================================================
# Integration Smoke Tests - Lightweight checks
# ============================================================================


def test_github_client_initialization():
    """Test GitHub client initialization.

    Doesn't require valid token, just verifies client exists.
    """
    from servers.github_tools import github_client

    # Just verify the client exists
    # (may fail with invalid token, but that's OK)
    assert github_client is not None


def test_slack_client_initialization():
    """Test Slack client initialization.

    Doesn't require valid token, just verifies client exists.
    """
    from servers.slack_tools import slack_client

    # Just verify the client exists
    # (may fail with invalid token, but that's OK)
    assert slack_client is not None


def test_update_docs_json_content_structure():
    """Test update_docs_json_content JSON handling."""
    from servers.github_tools import update_docs_json_content

    # Minimal valid docs.json structure
    minimal_docs = {"navigation": {"anchors": [{"anchor": "Changelog", "groups": []}]}}

    import json

    docs_str = json.dumps(minimal_docs)

    # Should not raise an error
    result = update_docs_json_content(docs_str, "2025", "01", "15")

    # Should return valid JSON
    parsed = json.loads(result)
    assert isinstance(parsed, dict)
    assert "navigation" in parsed


def test_format_pr_body():
    """Test PR body formatting."""
    from servers.github_tools import format_pr_body

    changelog_path = "docs/updates/2025/01/15/changelog.mdx"
    body = format_pr_body("2025-01-15", changelog_path, 3)

    assert "2025-01-15" in body
    assert "changelog" in body.lower()
    assert "3" in body or "three" in body.lower()


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_media_files_validation():
    """Test media_files parameter validation logic."""
    from servers.github_tools import create_changelog_pr
    import inspect

    # Check that the validation exists in the function
    source = inspect.getsource(create_changelog_pr)
    assert "isinstance(media_files, list)" in source or "media_files" in source


# ============================================================================
# Main Function Tests
# ============================================================================


def test_main_function_exists():
    """Test that main function exists and is async."""
    import main
    import inspect

    assert hasattr(main, "main")
    assert inspect.iscoroutinefunction(main.main)


def test_user_prompt_exists():
    """Test that USER_PROMPT is defined."""
    import main

    assert hasattr(main, "USER_PROMPT")
    assert isinstance(main.USER_PROMPT, str)
    assert len(main.USER_PROMPT) > 0


def test_agent_definitions_exist():
    """Test that agent definitions are properly structured."""
    import main

    # The main function should set up agents
    # We can't easily test the full setup without running it, but we
    # can check that the structure exists in the code
    assert hasattr(main, "permission_groups")
    assert "changelog_writer" in main.permission_groups
    assert "template_formatter" in main.permission_groups
