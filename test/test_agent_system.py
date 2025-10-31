#!/usr/bin/env python3
"""Tests for agent system initialization and configuration.

These tests ensure the agent system can be configured correctly and will catch
breaking changes in agent definitions before they reach CI/CD.
"""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


# ============================================================================
# Helper Functions
# ============================================================================


def get_main_module():
    """Safely import main module, skipping if credentials not available."""
    if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_REPO"):
        pytest.skip("GITHUB_TOKEN or GITHUB_REPO not set")

    try:
        import main

        return main
    except ValueError:
        pytest.skip("GitHub tools require GITHUB_TOKEN and GITHUB_REPO")


# ============================================================================
# Agent Configuration Tests
# ============================================================================


def test_agent_definitions_exist():
    """Verify all required agent definitions exist."""
    main = get_main_module()

    required_agents = [
        "changelog_writer",
        "template_formatter",
        "review_and_feedback",
        "pr_writer",
    ]

    # Agents are defined in ClaudeAgentOptions, check permission_groups instead
    assert hasattr(main, "permission_groups"), "permission_groups should exist"

    for agent_name in required_agents:
        assert (
            agent_name in main.permission_groups
        ), f"Agent {agent_name} should have permission group defined"


def test_agent_system_can_initialize():
    """Verify ClaudeAgentOptions can be created without errors."""
    from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition

    # This will fail if there are syntax errors, import errors,
    # or config issues
    try:
        options = ClaudeAgentOptions(
            agents={
                "changelog_writer": AgentDefinition(
                    description="Test agent",
                    prompt="Test prompt",
                    model="haiku",
                    tools=[],
                ),
            },
            system_prompt="Test system prompt",
            permission_mode="bypassPermissions",
            cwd="./",
            mcp_servers={},
        )
        assert options is not None
        assert hasattr(options, "agents")
    except Exception as e:
        pytest.fail(f"Agent system initialization failed: {e}")


def test_permission_groups_are_valid():
    """Verify permission groups reference valid permissions."""
    main = get_main_module()

    # Check each agent's permission group
    for agent_name, permissions in main.permission_groups.items():
        # For template_formatter, permissions are strings directly
        if isinstance(permissions, list):
            # Verify permissions are strings
            for perm in permissions:
                assert isinstance(
                    perm, str
                ), f"Permission in {agent_name} should be string"
                # Check if it's a valid format (file perm, MCP, or special)
                file_prefixes = ("Read(", "Write(", "Edit(", "Glob(")
                is_file_perm = perm.startswith(file_prefixes)
                is_mcp_perm = perm.startswith("mcp__") or perm in [
                    "WebSearch",
                    "mcp__mintlify__SearchMintlify",
                    "mcp__replit__SearchReplit",
                ]
                assert (
                    is_file_perm or is_mcp_perm or perm.startswith("mcp__")
                ), f"Invalid permission format in {agent_name}: {perm}"


def test_get_today_changelog_permissions():
    """Verify today's changelog permissions function works correctly."""
    main = get_main_module()
    from datetime import datetime

    permissions = main.get_today_changelog_permissions()

    assert isinstance(permissions, list)
    assert len(permissions) > 0

    # Check that today's date is in at least one permission
    today = datetime.now().strftime("%Y-%m-%d")
    permissions_str = " ".join(permissions)
    assert today in permissions_str, "Today's date should be in permissions"


def test_user_prompt_exists_and_valid():
    """Verify USER_PROMPT is defined and has expected content."""
    main = get_main_module()

    assert hasattr(main, "USER_PROMPT")
    assert isinstance(main.USER_PROMPT, str)
    assert len(main.USER_PROMPT) > 0

    # Check for key workflow mentions
    required_mentions = ["changelog_writer", "template_formatter", "pr_writer"]
    prompt_lower = main.USER_PROMPT.lower()
    for mention in required_mentions:
        assert mention in prompt_lower, f"USER_PROMPT should mention {mention}"


# ============================================================================
# Agent Configuration Validation
# ============================================================================


def test_all_agents_have_tools():
    """Verify each agent has at least one tool/permission defined."""
    main = get_main_module()

    for agent_name, permissions in main.permission_groups.items():
        msg = f"Agent {agent_name} should have permissions"
        assert len(permissions) > 0, msg


def test_template_formatter_has_restricted_permissions():
    """Verify template_formatter only has today's file permissions."""
    main = get_main_module()
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    permissions = main.permission_groups["template_formatter"]

    # Should only have permissions for today's file
    for perm in permissions:
        msg = f"template_formatter permission should include {today}"
        assert today in perm, msg


# ============================================================================
# Configuration Files Validation
# ============================================================================


def test_prompt_files_exist():
    """Verify all required prompt files exist (agents reference them)."""
    project_root = Path(__file__).parent.parent
    prompts_dir = project_root / "prompts"

    # Files referenced in agent prompts
    required_files = [
        "brand_guidelines.md",
        "changelog_template.md",
        "docs_style_guide.md",
        "good_docs.md",
    ]

    for filename in required_files:
        file_path = prompts_dir / filename
        assert file_path.exists(), (
            f"Required prompt file {filename} missing - "
            f"agents will fail to load prompts"
        )


def test_prompts_can_be_read():
    """Verify prompt files can be read (catches encoding/format issues)."""
    project_root = Path(__file__).parent.parent
    prompts_dir = project_root / "prompts"

    prompt_files = [
        "brand_guidelines.md",
        "changelog_template.md",
        "docs_style_guide.md",
        "good_docs.md",
    ]

    for filename in prompt_files:
        file_path = prompts_dir / filename
        try:
            content = file_path.read_text(encoding="utf-8")
            msg = f"{filename} should not be empty"
            assert len(content) > 0, msg
        except Exception as e:
            pytest.fail(f"Failed to read {filename}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
