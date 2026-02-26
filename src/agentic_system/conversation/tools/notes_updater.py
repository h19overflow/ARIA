"""
Notes state mutation helpers for ConversationAgent.

Encapsulates how take_note / commit_notes tool calls
mutate the ConversationNotes within ConversationState.
"""
import json
import logging
from typing import Any, Dict

from ..core.state import ConversationState

logger = logging.getLogger(__name__)

_LIST_FIELDS = {"constraints", "required_integrations"}
_OPTIONAL_FIELDS = {
    "data_transform", "trigger_type", "trigger_service",
    "trigger_schedule", "trigger_event", "transform",
    "destination_service", "destination_action", "destination_format",
}


def update_notes_state(
    state: ConversationState, args: Dict[str, Any]
) -> None:
    """Update notes state from take_note arguments."""
    key, value = args.get("key"), args.get("value")
    if not key:
        return
    if value is None:
        _delete_note(state, key)
    else:
        _set_note(state, key, value)


def _delete_note(state: ConversationState, key: str) -> None:
    """Remove a note, resetting the schema field if it exists."""
    state.notes.raw_notes.pop(key, None)
    if not hasattr(state.notes, key):
        return
    if key in _LIST_FIELDS:
        setattr(state.notes, key, [])
    elif key in _OPTIONAL_FIELDS:
        setattr(state.notes, key, None)
    else:
        setattr(state.notes, key, "")


def _set_note(
    state: ConversationState, key: str, value: str
) -> None:
    """Record a note, appending to lists or setting directly."""
    state.notes.raw_notes[key] = value
    if not hasattr(state.notes, key):
        return
    if key in _LIST_FIELDS:
        current = getattr(state.notes, key)
        items = [v.strip() for v in value.split(",") if v.strip()]
        for item in items:
            if item not in current:
                current.append(item)
    else:
        setattr(state.notes, key, value)


def update_notes_on_scan_credentials(
    state: ConversationState, scan_data: dict
) -> None:
    """Sync pending/resolved from scan_credentials result into state.notes."""
    pending = scan_data.get("pending", [])
    if isinstance(pending, list) and pending:
        state.notes.pending_credential_types = pending
    for item in scan_data.get("resolved", []):
        if isinstance(item, dict) and item.get("type") and item.get("id"):
            state.notes.resolved_credential_ids[item["type"]] = item["id"]


def update_notes_on_save_credential_result(
    state: ConversationState, tool_result: str
) -> None:
    """Update resolved_credential_ids from a successful save_credential result."""
    try:
        data = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
        if data.get("success") and data.get("id") and data.get("type"):
            cred_type = data["type"]
            state.notes.resolved_credential_ids[cred_type] = data["id"]
            state.notes.pending_credential_types = [
                t for t in state.notes.pending_credential_types if t != cred_type
            ]
    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        logger.warning("Failed to parse save_credential result: %s", e)


def update_notes_on_credentials_commit(
    state: ConversationState, summary: str
) -> None:
    """Mark credentials as committed."""
    state.notes.credentials_committed = True
