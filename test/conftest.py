"""Pytest configuration and shared fixtures."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "asyncio: marks tests as async (pytest-asyncio)")


def pytest_collection_modifyitems(config, items):
    """Skip test_mcp_server.py as it's not a test file."""
    for item in items:
        if "test_mcp_server" in str(item.fspath):
            pytest.skip(reason="Not a test file - standalone MCP server", item=item)
