"""LangChain tools for ARIA Phase 0 — Conversation Agent note-taking."""
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class TakeNoteInput(BaseModel):
    """Input schema for the take_note tool."""
    key: str = Field(
        description="The category or name of the note (e.g., 'trigger', 'destination', 'data_transform', 'constraint')."
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
    """Records, updates, or deletes a specific requirement or note for the workflow.
    
    Use this tool whenever the user provides new information about what they want to build.
    Common keys include: "trigger", "destination", "data_transform", "constraint", "required_integrations".
    
    If the user changes their mind and wants to remove a requirement, call this tool 
    with the corresponding key and set `value` to None to explicitly delete it.
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
