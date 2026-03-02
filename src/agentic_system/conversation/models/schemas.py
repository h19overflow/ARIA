from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


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
    # Credential-gathering fields (Phase 1 merged into conversation)
    required_nodes: List[str] = Field(
        default_factory=list,
        description="n8n node type keys needed for the workflow.",
    )
    resolved_credential_ids: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of credential_type to n8n credential ID.",
    )
    pending_credential_types: List[str] = Field(
        default_factory=list,
        description="Credential types not yet saved in n8n.",
    )
    credentials_committed: bool = Field(
        default=False,
        description="True when all credentials are resolved and ready for build.",
    )

    @field_validator("required_integrations", mode="before")
    @classmethod
    def normalize_integrations_list(cls, value: list) -> list[str]:
        """Split any CSV strings and deduplicate."""
        if not isinstance(value, list):
            return value
        result: list[str] = []
        for item in value:
            if isinstance(item, str) and "," in item:
                for part in item.split(","):
                    stripped = part.strip()
                    if stripped and stripped not in result:
                        result.append(stripped)
            else:
                stripped = item.strip() if isinstance(item, str) else item
                if stripped and stripped not in result:
                    result.append(stripped)
        return result
