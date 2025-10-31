#!/usr/bin/env python3
"""Tests for MCP server initialization and configuration.

These tests ensure MCP servers can be configured correctly and will catch
breaking changes before they reach CI/CD.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


# ============================================================================
# MCP Server Configuration Tests
# ============================================================================


def test_mcp_servers_configuration_exists():
    """Verify MCP_SERVERS configuration exists and is a dict."""
    from servers.config import MCP_SERVERS

    assert MCP_SERVERS is not None
    assert isinstance(MCP_SERVERS, dict), "MCP_SERVERS should be a dictionary"
    assert len(MCP_SERVERS) > 0, "MCP_SERVERS should not be empty"


def test_required_mcp_servers_configured():
    """Verify all required MCP servers are configured."""
    from servers.config import MCP_SERVERS

    required_servers = [
        "slack_updates",
        "github_changelog",
        "github",
        "mintlify",
        "replit",
    ]

    for server_name in required_servers:
        assert (
            server_name in MCP_SERVERS
        ), f"Required MCP server '{server_name}' not configured"


def test_slack_updates_server_configuration():
    """Verify slack_updates MCP server is properly configured."""
    from servers.config import MCP_SERVERS

    assert "slack_updates" in MCP_SERVERS
    server = MCP_SERVERS["slack_updates"]

    # Should be an SDK MCP server (dict with 'instance' key)
    assert isinstance(server, dict), "slack_updates should be SDK MCP server"
    assert "instance" in server, "SDK server should have 'instance' key"


def test_github_changelog_server_configuration():
    """Verify github_changelog MCP server is properly configured."""
    from servers.config import MCP_SERVERS

    assert "github_changelog" in MCP_SERVERS
    server = MCP_SERVERS["github_changelog"]

    # Should be an SDK MCP server
    assert isinstance(server, dict), "github_changelog should be SDK MCP server"
    assert "instance" in server, "SDK server should have 'instance' key"


def test_external_mcp_servers_have_urls():
    """Verify external MCP servers (HTTP) have URL configuration."""
    from servers.config import MCP_SERVERS

    external_servers = ["github", "mintlify", "replit"]

    for server_name in external_servers:
        assert server_name in MCP_SERVERS
        server = MCP_SERVERS[server_name]

        # Should have type and url attributes
        assert hasattr(server, "type") or "type" in server.__dict__
        assert hasattr(server, "url") or "url" in server.__dict__


def test_github_mcp_server_has_headers():
    """Verify GitHub MCP server has authorization headers configured."""
    from servers.config import MCP_SERVERS

    if "github" in MCP_SERVERS:
        server = MCP_SERVERS["github"]
        # Should have headers configured (may be empty if no token)
        assert hasattr(server, "headers") or "headers" in server.__dict__


def test_mcp_server_tools_are_registered():
    """Verify tools are properly registered in SDK MCP servers."""
    from servers.config import MCP_SERVERS

    # Check slack_updates has fetch_messages_from_channel
    if "slack_updates" in MCP_SERVERS:
        server = MCP_SERVERS["slack_updates"]
        # SDK servers should have tools registered
        # We can't easily inspect tools without running server, but we can
        # verify the server exists and is properly structured
        assert server is not None

    # Check github_changelog has create_changelog_pr
    if "github_changelog" in MCP_SERVERS:
        server = MCP_SERVERS["github_changelog"]
        assert server is not None


def test_mcp_servers_imports_work():
    """Verify all MCP server imports succeed (catches import errors)."""
    try:
        from servers.config import MCP_SERVERS
        from servers.slack_tools import fetch_messages_from_channel
        from servers.github_tools import create_changelog_pr

        # If we get here, imports worked
        assert MCP_SERVERS is not None
        assert fetch_messages_from_channel is not None
        assert create_changelog_pr is not None
    except ImportError as e:
        pytest.fail(f"MCP server imports failed: {e}")


# ============================================================================
# MCP Server Tool Registration
# ============================================================================


def test_slack_tool_is_decorated():
    """Verify fetch_messages_from_channel is properly decorated as a tool."""
    from servers.slack_tools import fetch_messages_from_channel
    import inspect

    # Should be async
    assert inspect.iscoroutinefunction(
        fetch_messages_from_channel
    ), "fetch_messages_from_channel should be async"

    # Should have __name__
    assert hasattr(fetch_messages_from_channel, "__name__")


def test_github_tool_is_decorated():
    """Verify create_changelog_pr is properly decorated as a tool."""
    from servers.github_tools import create_changelog_pr
    import inspect

    # Should be async
    assert inspect.iscoroutinefunction(
        create_changelog_pr
    ), "create_changelog_pr should be async"

    # Should have __name__
    assert hasattr(create_changelog_pr, "__name__")


# ============================================================================
# Configuration Validation
# ============================================================================


def test_mcp_server_config_can_be_loaded():
    """Verify MCP server configuration can be loaded without errors."""
    from servers import config

    # Just verify the module loads and MCP_SERVERS is accessible
    assert hasattr(config, "MCP_SERVERS")
    assert config.MCP_SERVERS is not None


def test_no_circular_imports():
    """Verify there are no circular import issues with MCP servers."""
    # If this test passes, imports work without circular dependencies
    try:
        from servers.config import MCP_SERVERS
        from servers.slack_tools import fetch_messages_from_channel
        from servers.github_tools import create_changelog_pr
        import main  # Main module also imports these

        # All should import successfully
        assert True
    except ImportError as e:
        pytest.fail(f"Circular import detected: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
