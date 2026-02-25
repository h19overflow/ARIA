"""
Notes state mutation helpers for ConversationAgent.

Encapsulates how take_note / commit_notes tool calls
mutate the ConversationNotes within ConversationState.
"""
from typing import Any, Dict

from .state import ConversationState

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
        if value not in current:
            current.append(value)
    else:
        setattr(state.notes, key, value)
