from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class TakeNoteInput(BaseModel):
    """Input schema for taking or updating a conversation note."""
    key: str = Field(
        ..., 
        description="The key of the note to take (e.g., 'trigger', 'destination', 'data_transform', 'constraint')."
    )
    value: Optional[str] = Field(
        None, 
        description="Free-form text for the note. If None, the note is deleted."
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
        description="Any data transformation required between trigger and destination."
    )
    constraints: List[str] = Field(
        default_factory=list, 
        description="Specific rules, filters, or conditions the workflow must follow."
    )
    required_integrations: List[str] = Field(
        default_factory=list, 
        description="List of third-party services or apps involved."
    )
    raw_notes: Dict[str, str] = Field(
        default_factory=dict, 
        description="Raw key-value pairs of all notes taken."
    )
