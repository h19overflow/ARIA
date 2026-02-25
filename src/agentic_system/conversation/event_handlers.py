"""
Extracted event-handling helpers for ConversationAgent.

Keeps the agent module focused on orchestration while this module
owns message construction, tool-state updates, and result extraction.
"""
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.messages import AIMessage, ToolMessage

from pydantic import BaseModel

from .state import ConversationState
from .notes_updater import update_notes_state


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a Pydantic model or dict to a plain dict."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return {"key": str(obj)}


def extract_result_string(tool_result: Any) -> str:
    """Coerce a tool result into a display-friendly string."""
    if hasattr(tool_result, "content"):
        return str(tool_result.content)
    return str(tool_result)


async def handle_tool_end_state(
    state: ConversationState,
    tool_name: str,
    current_tool_calls: List[Dict[str, Any]],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Yield tool_event SSE and mutate state for known tools."""
    tool_args = next(
        (tc["args"] for tc in reversed(current_tool_calls)
         if tc["name"] == tool_name),
        {},
    )
    if tool_name == "take_note":
        update_notes_state(state, tool_args)
        yield {"type": "tool_event", "tool": "take_note", "data": tool_args}
    elif tool_name == "batch_notes":
        raw_notes = tool_args.get("notes", [])
        note_pairs: List[Dict[str, Any]] = []
        for note in raw_notes:
            note_dict = _to_dict(note)
            update_notes_state(state, note_dict)
            note_pairs.append({"key": note_dict.get("key", "?"), "value": note_dict.get("value")})
        yield {
            "type": "tool_event",
            "tool": "batch_notes",
            "data": {"count": len(raw_notes), "notes": note_pairs},
        }
    elif tool_name == "commit_notes":
        if state.committed:
            yield {
                "type": "tool_event",
                "tool": "commit_notes",
                "data": {"skipped": True, "reason": "already_committed"},
            }
        else:
            state.notes.summary = tool_args.get("summary", "")
            state.committed = True
            yield {
                "type": "tool_event",
                "tool": "commit_notes",
                "data": tool_args,
            }


def capture_ai_message(
    event: Dict[str, Any], state: ConversationState
) -> None:
    """Append assistant message to state on on_chat_model_end."""
    if event.get("event") != "on_chat_model_end":
        return
    ai_msg = event["data"].get("output")
    if not isinstance(ai_msg, AIMessage):
        return
    state_msg: Dict[str, Any] = {
        "role": "assistant",
        "content": ai_msg.content or "",
    }
    if getattr(ai_msg, "tool_calls", None):
        state_msg["tool_calls"] = ai_msg.tool_calls
    if getattr(ai_msg, "invalid_tool_calls", None):
        state_msg["invalid_tool_calls"] = ai_msg.invalid_tool_calls
    state.messages.append(state_msg)


def capture_tool_message(
    event: Dict[str, Any], state: ConversationState
) -> None:
    """Append tool result message to state on on_tool_end."""
    if event.get("event") != "on_tool_end":
        return
    tool_output = event["data"].get("output")
    tool_call_id = _find_tool_call_id(state, event.get("name", ""))

    if isinstance(tool_output, ToolMessage):
        state.messages.append({
            "role": "tool",
            "content": tool_output.content,
            "tool_call_id": tool_output.tool_call_id,
        })
    else:
        state.messages.append({
            "role": "tool",
            "content": str(tool_output),
            "tool_call_id": tool_call_id,
        })


def _find_tool_call_id(
    state: ConversationState, tool_name: str
) -> str:
    """Look up the tool_call_id from the last assistant message."""
    if not state.messages or state.messages[-1]["role"] != "assistant":
        return ""
    for tc in state.messages[-1].get("tool_calls", []):
        if tc["name"] == tool_name:
            return tc["id"]
    return ""
