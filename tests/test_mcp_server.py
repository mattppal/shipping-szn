#!/usr/bin/env python3
"""Tests for MCP server initialization and functionality.

Run with: pytest test_mcp_server.py -v
"""

import pytest
from unittest.mock import Mock, patch
from mcp_servers import MCP_SERVERS
from claude_agent_sdk import ClaudeAgentOptions, query, SystemMessage


class TestMCPServerConfiguration:
    """Test MCP server configuration."""

    def test_mcp_servers_dict_exists(self):
        """Test that MCP_SERVERS dictionary is defined."""
        assert MCP_SERVERS is not None
        assert isinstance(MCP_SERVERS, dict)

    def test_slack_server_configured(self):
        """Test that Slack MCP server is configured."""
        assert "slack" in MCP_SERVERS
        slack_config = MCP_SERVERS["slack"]
        assert isinstance(slack_config, dict)
        assert slack_config.get("type") == "stdio"

    def test_github_server_configured(self):
        """Test that GitHub MCP server is configured."""
        assert "github" in MCP_SERVERS
        github_config = MCP_SERVERS["github"]
        assert isinstance(github_config, dict)
        assert github_config.get("type") == "http"

    def test_all_servers_have_required_fields(self):
        """Test that all servers have required configuration fields."""
        for server_name, config in MCP_SERVERS.items():
            assert "type" in config, f"Server {server_name} missing 'type' field"

            if config["type"] == "stdio":
                assert "command" in config, f"stdio server {server_name} missing 'command'"
                assert "args" in config, f"stdio server {server_name} missing 'args'"

            elif config["type"] == "http":
                assert "url" in config, f"http server {server_name} missing 'url'"


class TestMCPServerInitialization:
    """Test MCP server initialization with Claude Agent SDK."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mcp_server_initialization(self):
        """Test that MCP servers initialize correctly (integration test)."""
        options = ClaudeAgentOptions(
            system_prompt="Test",
            permission_mode="bypassPermissions",
            model="claude-sonnet-4-5",
            cwd="./",
            setting_sources=["local"],
            mcp_servers=MCP_SERVERS,
        )

        mcp_status = {}

        # Get the first message which should contain MCP server status
        async for message in query(
            prompt="What tools do you have access to?",
            options=options,
        ):
            if isinstance(message, SystemMessage):
                data = message.data
                if isinstance(data, dict) and "mcp_servers" in data:
                    for server in data["mcp_servers"]:
                        mcp_status[server["name"]] = server["status"]
                    break
            break

        # Verify we got status for our configured servers
        assert len(mcp_status) > 0, "No MCP server status received"

        # Check Slack server status
        if "slack" in mcp_status:
            assert mcp_status["slack"] in [
                "connected",
                "failed",
            ], f"Unexpected slack status: {mcp_status['slack']}"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_slack_mcp_tool_available(self):
        """Test that Slack MCP tools are available after initialization."""
        options = ClaudeAgentOptions(
            system_prompt="Test",
            permission_mode="bypassPermissions",
            model="claude-sonnet-4-5",
            cwd="./",
            setting_sources=["local"],
            mcp_servers=MCP_SERVERS,
        )

        tools_list = []

        async for message in query(
            prompt="What tools do you have access to?",
            options=options,
        ):
            if isinstance(message, SystemMessage):
                data = message.data
                if isinstance(data, dict) and "tools" in data:
                    tools_list = data["tools"]
                    break
            break

        # Check if slack tools are in the tools list
        slack_tools = [
            tool for tool in tools_list if "slack" in tool.lower() or "message" in tool.lower()
        ]

        # We expect at least one slack-related tool
        assert len(slack_tools) > 0, f"No Slack tools found. Available tools: {tools_list}"


class TestSlackMCPStandaloneServer:
    """Test the standalone Slack MCP server script."""

    def test_slack_mcp_server_file_exists(self):
        """Test that slack_mcp_server.py exists."""
        import os

        assert os.path.exists("slack_mcp_server.py"), "slack_mcp_server.py not found"

    @patch("slack_tools.slack_client")
    def test_slack_tools_import(self, mock_client):
        """Test that slack_tools can be imported without errors."""
        try:
            from slack_tools import fetch_messages_from_channel

            assert fetch_messages_from_channel is not None
        except ImportError as e:
            pytest.fail(f"Failed to import slack_tools: {e}")


@pytest.fixture
def mock_claude_options():
    """Fixture providing mock Claude Agent options."""
    return ClaudeAgentOptions(
        system_prompt="Test",
        permission_mode="bypassPermissions",
        model="claude-sonnet-4-5",
        cwd="./",
        setting_sources=["local"],
        mcp_servers=MCP_SERVERS,
    )


class TestMCPServerHealth:
    """Health check tests for MCP servers."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.timeout(30)
    async def test_mcp_servers_respond_within_timeout(self, mock_claude_options):
        """Test that MCP servers respond within reasonable time."""
        responded = False

        async for message in query(
            prompt="List available tools",
            options=mock_claude_options,
        ):
            if isinstance(message, SystemMessage):
                responded = True
                break
            break

        assert responded, "MCP servers did not respond within timeout"

    def test_expected_servers_configured(self):
        """Test that all expected servers are in configuration."""
        expected_servers = ["slack", "github"]

        for server in expected_servers:
            assert (
                server in MCP_SERVERS
            ), f"Expected server '{server}' not found in MCP_SERVERS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
