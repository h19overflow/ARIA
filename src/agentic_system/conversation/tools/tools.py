"""LangChain tools for ARIA Phase 0 — Conversation Agent note-taking."""
from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class TakeNoteInput(BaseModel):
    """Input schema for the take_note tool."""
    key: str = Field(
        description=(
            "The sub-key for the note. Use: trigger_type, trigger_service, "
            "trigger_schedule, trigger_event, action_1/action_2/..., transform, "
            "destination_service, destination_action, destination_format, "
            "destination_2_service, destination_2_action, destination_3_service, "
            "constraint, required_integrations."
        ),
    )
    value: Optional[str] = Field(
        default=None,
        description="The free-form text content of the note. If None, the note for the given key is explicitly deleted."
    )


class BatchNotesInput(BaseModel):
    """Input schema for the batch_notes tool."""
    notes: List[TakeNoteInput] = Field(
        description="List of notes to record in a single call."
    )


class RemoveNoteInput(BaseModel):
    """Input schema for the remove_note tool."""
    key: str = Field(
        description="The list field to remove from: 'required_integrations' or 'constraints'.",
    )
    value: str = Field(
        description="The exact item to remove from the list.",
    )


class CommitNotesInput(BaseModel):
    """Input schema for the commit_notes tool."""
    summary: str = Field(
        description="A concise, one-line summary of the full workflow intent."
    )


@tool("batch_notes", args_schema=BatchNotesInput)
async def batch_notes(notes: List) -> str:
    """Record multiple workflow requirement notes in one call.

    Use this as the PRIMARY note-taking tool. Pass all notes gathered
    from the current user message in a single call instead of calling
    take_note repeatedly.

    Each note has a key (sub-key from taxonomy) and optional value.
    """
    keys = [
        getattr(n, "key", n.get("key", "?") if isinstance(n, dict) else "?")
        for n in notes
    ]
    return f"Action recorded: Saved {len(notes)} notes for keys: {', '.join(keys)}."


@tool("take_note", args_schema=TakeNoteInput)
async def take_note(key: str, value: Optional[str] = None) -> str:
    """Records, updates, or deletes a single workflow requirement note.

    Use for corrections or single-note updates. For multiple notes,
    prefer batch_notes instead.

    Set `value` to None to delete a note.
    """
    if value is None:
        return f"Action recorded: Deleted note for key '{key}'."
    return f"Action recorded: Saved note for key '{key}' with value '{value}'."


@tool("remove_note", args_schema=RemoveNoteInput)
async def remove_note(key: str, value: str) -> str:
    """Remove a single item from a list field (required_integrations or constraints).

    Use when the user wants to drop, remove, or exclude a specific
    service or constraint. Do NOT use take_note with value=null — that
    wipes the entire list.
    """
    return f"Action recorded: Removed '{value}' from '{key}'."


@tool("commit_notes", args_schema=CommitNotesInput)
async def commit_notes(summary: str) -> str:
    """Commits the gathered requirements and finalizes the conversation phase.

    Call when core elements (trigger, action, destination) are captured.
    Record any final notes AND commit in the same turn when possible.
    """
    return f"Action recorded: Committed notes with summary '{summary}'."


# Re-export credential tools (merged from Phase 1 Preflight)
from .credential_tools import (  # noqa: E402, F401
    scan_credentials,
    set_shared_required_nodes,
    get_credential_schema,
    save_credential,
    commit_preflight,
)

__all__ = [
    "batch_notes", "take_note", "remove_note", "commit_notes",
    "scan_credentials", "set_shared_required_nodes",
    "get_credential_schema", "save_credential", "commit_preflight",
]
