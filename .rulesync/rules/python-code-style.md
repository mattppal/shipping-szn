---
targets: ['*']
description: "Python code style, formatting, and conventions"
globs: ["**/*.py"]
---

# Python Code Style

## Python Standards

- **Formatting:** Use Black (88 char line length, configured in pyproject.toml)
- **Type hints:** Include for function parameters and returns: `def func(param: str) -> dict:`
- **Strings:** Double quotes consistently, prefer f-strings
- **Imports:** Group as standard library → third-party → local. Use absolute imports: `from servers.config import MCP_SERVERS`
- **Environment:** Load `dotenv` at module top: `load_dotenv()` before `os.getenv()`

## Async Patterns

See [main.py](../main.py) for complete async implementation example.

```python
# Entry point
async def main():
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt=USER_PROMPT)
        async for message in client.receive_response():
            display_message(message)

asyncio.run(main())
```

## Naming Conventions

- **Functions:** `snake_case` (e.g., `fetch_messages_from_channel`)
- **Classes:** `PascalCase` (e.g., `AgentDefinition`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `GITHUB_TOKEN`)
- **Agent names:** Match role: `changelog_writer`, `template_formatter`, `pr_writer`

## Error Handling

- Use specific exceptions: `GithubException`, `ValueError`
- Validate env vars at module load: `if not GITHUB_TOKEN: raise ValueError("GITHUB_TOKEN not set")`
- Log with context: `logger.error(f"Error uploading {file_path}: {str(e)}")`
- Never expose secrets in errors

