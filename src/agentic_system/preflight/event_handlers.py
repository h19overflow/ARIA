"""Event handlers for PreflightAgent — tool state updates and SSE events."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.messages import AIMessage, ToolMessage

from .state import PreflightState
from .notes_updater import (
    update_notes_on_commit,
    update_notes_on_save_credential,
    update_notes_on_save_credential_result,
)

logger = logging.getLogger(__name__)


def extract_result_string(tool_result: Any) -> str:
    """Coerce a tool result into a display-friendly string."""
    if hasattr(tool_result, "content"):
        return str(tool_result.content)
    return str(tool_result)


async def handle_tool_end_state(
    state: PreflightState,
    tool_name: str,
    tool_result: Any,
    current_tool_calls: List[Dict[str, Any]],
) -> AsyncGenerator[Dict[str, Any], None]:
    """Yield tool_event SSE and mutate state for known preflight tools."""
    tool_args = next(
        (tc["args"] for tc in reversed(current_tool_calls) if tc["name"] == tool_name),
        {},
    )
    result_str = extract_result_string(tool_result)

    if tool_name == "scan_credentials":
        scan_data = _parse_json_safe(result_str)
        _apply_scan_to_notes(state, scan_data)
        yield {"type": "tool_event", "tool": "scan_credentials", "data": scan_data}

    elif tool_name == "save_credential":
        update_notes_on_save_credential(state, tool_args)
        update_notes_on_save_credential_result(state, result_str)
        result_data = _parse_json_safe(result_str)
        yield {
            "type": "tool_event",
            "tool": "save_credential",
            "data": {
                "credential_type": tool_args.get("credential_type", ""),
                "success": result_data.get("success", False),
                "id": result_data.get("id", ""),
                "resolved": dict(state.notes.resolved_credential_ids),
                "pending": list(state.notes.pending_credential_types),
            },
        }

    elif tool_name == "commit_preflight":
        summary = tool_args.get("summary", "")
        update_notes_on_commit(state, summary)
        yield {"type": "tool_event", "tool": "commit_preflight", "data": {"summary": summary, "committed": True}}


def capture_ai_message(event: Dict[str, Any], state: PreflightState) -> None:
    """Append assistant message to state on on_chat_model_end."""
    if event.get("event") != "on_chat_model_end":
        return
    ai_msg = event["data"].get("output")
    if not isinstance(ai_msg, AIMessage):
        return
    state_msg: Dict[str, Any] = {"role": "assistant", "content": ai_msg.content or ""}
    if getattr(ai_msg, "tool_calls", None):
        state_msg["tool_calls"] = ai_msg.tool_calls
    if getattr(ai_msg, "invalid_tool_calls", None):
        state_msg["invalid_tool_calls"] = ai_msg.invalid_tool_calls
    state.messages.append(state_msg)


def capture_tool_message(event: Dict[str, Any], state: PreflightState) -> None:
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


def _find_tool_call_id(state: PreflightState, tool_name: str) -> str:
    """Look up the tool_call_id from the last assistant message."""
    if not state.messages or state.messages[-1]["role"] != "assistant":
        return ""
    for tc in state.messages[-1].get("tool_calls", []):
        if tc["name"] == tool_name:
            return tc["id"]
    return ""


def _parse_json_safe(s: Any) -> dict:
    """Parse a JSON string to dict, returning a raw wrapper on failure."""
    if isinstance(s, dict):
        return s
    try:
        return json.loads(str(s))
    except (json.JSONDecodeError, TypeError):
        return {"raw": str(s)}


def _apply_scan_to_notes(state: PreflightState, scan_data: dict) -> None:
    """Sync pending/resolved lists from a scan_credentials result into state.notes."""
    pending = scan_data.get("pending", [])
    if isinstance(pending, list) and pending:
        state.notes.pending_credential_types = pending
    for item in scan_data.get("resolved", []):
        if isinstance(item, dict) and item.get("type") and item.get("id"):
            state.notes.resolved_credential_ids[item["type"]] = item["id"]
    if not state.notes.workflow_description:
        state.notes.workflow_description = _extract_workflow_description(state.messages)


def _extract_workflow_description(messages: list) -> str:
    """Extract the workflow intent line from the Phase 0 context message."""
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if "[Phase 0 Context]" in content:
                for line in content.splitlines():
                    if line.startswith("Workflow intent:"):
                        return line.removeprefix("Workflow intent:").strip()
    return ""
