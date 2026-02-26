"""LangChain message construction helpers.

Converts stored conversation dicts into LangChain message objects
for feeding back into the chat model.
"""
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)


def build_lc_messages(
    messages: List[Dict[str, Any]],
) -> List[BaseMessage]:
    """Convert stored message dicts into LangChain message objects."""
    lc_messages: List[BaseMessage] = []
    for msg in messages:
        role = msg["role"]
        if role == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif role == "assistant":
            lc_messages.append(_build_ai_message(msg))
        elif role == "tool":
            lc_messages.append(
                ToolMessage(
                    content=msg.get("content", ""),
                    tool_call_id=msg.get("tool_call_id", ""),
                )
            )
    return lc_messages


def _build_ai_message(msg: Dict[str, Any]) -> AIMessage:
    """Build an AIMessage from a stored assistant dict."""
    kwargs: Dict[str, Any] = {"content": msg.get("content", "")}
    if msg.get("tool_calls"):
        kwargs["tool_calls"] = msg["tool_calls"]
    if msg.get("invalid_tool_calls"):
        kwargs["invalid_tool_calls"] = msg["invalid_tool_calls"]
    return AIMessage(**kwargs)
