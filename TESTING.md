# Testing Guide

This document describes how to run tests for the Changelog Creation Crew (CCC) project.

## Test Structure

```
ccc/
├── test_slack_tools.py      # Unit tests for Slack tools
├── test_mcp_server.py        # Integration tests for MCP server
├── test_mcp_init.py          # MCP initialization tests
└── pytest.ini                # Pytest configuration
```

## Installation

Install test dependencies:

```bash
uv pip install pytest pytest-asyncio pytest-mock pytest-timeout
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Test Slack tools only
pytest test_slack_tools.py -v

# Test MCP server initialization only
pytest test_mcp_server.py -v
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest test_slack_tools.py::TestSlugify -v

# Run a specific test function
pytest test_slack_tools.py::TestSlugify::test_basic_slugify -v
```

### Run Tests by Marker

Tests are marked with different categories:

```bash
# Run only unit tests (fast, no external dependencies)
pytest -m unit

# Run only integration tests (require real Slack/MCP servers)
pytest -m integration

# Skip integration tests (useful for CI/CD)
pytest -m "not integration"

# Run slow tests
pytest -m slow
```

## Test Markers

- `@pytest.mark.unit` - Fast unit tests with mocked dependencies
- `@pytest.mark.integration` - Tests that require real services (Slack API, MCP servers)
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.asyncio` - Async tests (handled automatically)

## Environment Variables for Integration Tests

Integration tests require the following environment variables:

```bash
export SLACK_MCP_XOXP_TOKEN="xoxp-your-token"
export SLACK_CHANNEL_ID="C0123456789"
```

Integration tests will be skipped if these variables are not set.

## Test Coverage

To see test coverage (requires `pytest-cov`):

```bash
# Install coverage tool
uv pip install pytest-cov

# Run tests with coverage
pytest --cov=. --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

## Debugging Tests

### Run with Verbose Output

```bash
pytest -vv
```

### Stop on First Failure

```bash
pytest -x
```

### Show Print Statements

```bash
pytest -s
```

### Run Specific Test with Debugging

```bash
pytest test_slack_tools.py::test_slugify -vv -s
```

### Use Python Debugger

Add `import pdb; pdb.set_trace()` in your test and run:

```bash
pytest -s
```

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, patch

class TestMyFunction:
    """Test suite for my_function."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        result = my_function("input")
        assert result == "expected"

    @patch("module.dependency")
    def test_with_mock(self, mock_dep):
        """Test with mocked dependency."""
        mock_dep.return_value = "mocked"
        result = my_function()
        assert result == "expected"
```

### Integration Test Template

```python
import pytest

class TestIntegration:
    """Integration tests."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_api(self):
        """Test against real API."""
        result = await fetch_data()
        assert result is not None
```

## Continuous Integration

For CI/CD pipelines, run tests without integration tests:

```bash
# Run only unit tests (fast)
pytest -m "not integration" --tb=short

# Or skip slow tests
pytest -m "not slow" --tb=short
```

## Common Issues

### Async Tests Not Running

Make sure `pytest-asyncio` is installed:

```bash
uv pip install pytest-asyncio
```

### Import Errors

Ensure you're running tests from the project root:

```bash
cd /Users/matt/Developer/git-repos/ccc
pytest
```

### Token/Auth Errors in Integration Tests

Verify environment variables are set:

```bash
echo $SLACK_MCP_XOXP_TOKEN
echo $SLACK_CHANNEL_ID
```

### MCP Server Not Starting

Check that `slack_mcp_server.py` exists and is executable:

```bash
ls -la slack_mcp_server.py
python slack_mcp_server.py  # Should start server
```

## Best Practices

1. **Keep unit tests fast** - Mock external dependencies
2. **Mark integration tests** - Use `@pytest.mark.integration`
3. **Use descriptive names** - Test names should describe what they test
4. **One assertion per test** - Makes failures easier to diagnose
5. **Use fixtures** - Reuse common setup code
6. **Test edge cases** - Empty strings, None values, large inputs
7. **Don't test implementation details** - Test behavior, not internals

## Example Test Session

```bash
# Quick test run (unit tests only)
$ pytest -m "not integration" -q
........................                                            [100%]
24 passed in 2.34s

# Full test run (including integration tests)
$ pytest -v
test_slack_tools.py::TestSlugify::test_basic_slugify PASSED           [  4%]
test_slack_tools.py::TestSlugify::test_special_characters PASSED      [  8%]
...
test_mcp_server.py::TestMCPServerInitialization::test_mcp_server_initialization PASSED [100%]

========================== 45 passed in 12.34s ==========================
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
