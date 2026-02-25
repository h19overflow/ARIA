"""LangChain tools for ARIA Phase 0 — Conversation Agent note-taking."""
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class TakeNoteInput(BaseModel):
    """Input schema for the take_note tool."""
    key: str = Field(
        description=(
            "The sub-key for the note. Use: trigger_type, trigger_service, "
            "trigger_schedule, trigger_event, action_1/action_2/..., transform, "
            "destination_service, destination_action, destination_format, "
            "constraint, required_integrations."
        ),
    )
    value: Optional[str] = Field(
        default=None,
        description="The free-form text content of the note. If None, the note for the given key is explicitly deleted."
    )


class CommitNotesInput(BaseModel):
    """Input schema for the commit_notes tool."""
    summary: str = Field(
        description="A concise, one-line summary of the full workflow intent."
    )


@tool("take_note", args_schema=TakeNoteInput)
async def take_note(key: str, value: Optional[str] = None) -> str:
    """Records, updates, or deletes a workflow requirement note.

    Use granular sub-keys: trigger_type, trigger_service, trigger_schedule,
    trigger_event, action_1, action_2, transform, destination_service,
    destination_action, destination_format, constraint, required_integrations.

    Set `value` to None to delete a note.
    """
    if value is None:
        return f"Action recorded: Deleted note for key '{key}'."
    return f"Action recorded: Saved note for key '{key}' with value '{value}'."


@tool("commit_notes", args_schema=CommitNotesInput)
async def commit_notes(summary: str) -> str:
    """Commits the gathered requirements to long-term memory and finalizes the conversation phase.
    
    CRITICAL: Do not call this tool unless you have a complete understanding of the workflow,
    including at minimum a Trigger, Destination, AND Constraints. If any of these are missing, 
    ask the user for clarification instead of calling this tool.
    """
    return f"Action recorded: Committed notes with summary '{summary}'."
