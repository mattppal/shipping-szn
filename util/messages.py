from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from typing import Union


def display_message(
    msg: Union[UserMessage, AssistantMessage, SystemMessage, ResultMessage],
) -> None:
    """Display message content in a clean format."""

    if isinstance(msg, UserMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"User: {block.text}")
            elif isinstance(block, ToolResultBlock):
                print(
                    f"Tool Result: {block.content[:100] if block.content else 'None'}..."
                )
    elif isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                print(f"Claude: {block.text}")
            elif isinstance(block, ToolUseBlock):
                print(f"Using tool: {block.name}")
                if block.input:
                    print(f"  Input: {block.input}")
    elif isinstance(msg, SystemMessage):
        pass
    elif isinstance(msg, ResultMessage):
        print("Result ended")
        if msg.total_cost_usd:
            print(f"Cost: ${msg.total_cost_usd:.6f}")
