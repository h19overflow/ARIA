from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TakeNoteInput(BaseModel):
    """Input schema for taking or updating a conversation note."""
    key: str = Field(
        ...,
        description=(
            "The key of the note (e.g., 'trigger_type', "
            "'trigger_service', 'action_1', 'constraint')."
        ),
    )
    value: Optional[str] = Field(
        None,
        description="Free-form text for the note. If None, the note is deleted."
    )


class BatchNotesInput(BaseModel):
    """Input schema for recording multiple notes in a single call."""
    notes: List[TakeNoteInput] = Field(
        ...,
        description="List of notes to record. Each has a key and optional value.",
    )


class CommitNotesInput(BaseModel):
    """Input schema for committing the gathered requirements."""
    summary: str = Field(
        ...,
        description="A one-line summary of the full workflow intent."
    )


class ConversationNotes(BaseModel):
    """Structured state of the conversation requirements."""
    summary: str = Field(
        default="",
        description="One-line summary of the full workflow intent."
    )
    # Legacy broad fields (still accepted for backward compatibility)
    trigger: str = Field(
        default="",
        description="The event or system that starts the workflow."
    )
    destination: str = Field(
        default="",
        description="The final system or outcome of the workflow."
    )
    data_transform: Optional[str] = Field(
        default=None,
        description="Any data transformation required."
    )
    # Granular trigger fields
    trigger_type: Optional[str] = Field(
        default=None,
        description="schedule | webhook | email_poll | manual | event",
    )
    trigger_service: Optional[str] = Field(
        default=None,
        description="Which service triggers the workflow (e.g., Gmail).",
    )
    trigger_schedule: Optional[str] = Field(
        default=None,
        description="Schedule timing (e.g., 'Every day at 8 AM UTC').",
    )
    trigger_event: Optional[str] = Field(
        default=None,
        description="Event name if trigger_type is event-based.",
    )
    # Granular transform field
    transform: Optional[str] = Field(
        default=None,
        description="Data manipulation description (summarize, filter, etc.).",
    )
    # Granular destination fields
    destination_service: Optional[str] = Field(
        default=None,
        description="Target service (e.g., Telegram, Slack).",
    )
    destination_action: Optional[str] = Field(
        default=None,
        description="What to do at destination (e.g., send message).",
    )
    destination_format: Optional[str] = Field(
        default=None,
        description="Output format: plain text, JSON, HTML, markdown.",
    )
    # List fields (appended per call)
    constraints: List[str] = Field(
        default_factory=list,
        description="Rules, filters, or conditions."
    )
    required_integrations: List[str] = Field(
        default_factory=list,
        description="Third-party services or apps involved."
    )
    # Catch-all for dynamic keys (action_1, action_2, etc.)
    raw_notes: Dict[str, str] = Field(
        default_factory=dict,
        description="Raw key-value pairs of all notes taken."
    )
