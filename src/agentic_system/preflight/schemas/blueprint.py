"""Pydantic models for the Orchestrator's structured output."""
from pydantic import BaseModel, Field


class OrchestratorOutput(BaseModel):
    """Structured output from the Orchestrator agent.

    The orchestrator parses user intent and identifies required n8n node types.
    It does NOT identify credential types — that is the scanner's job.
    """
    intent_summary: str = Field(
        description="One-line summary of what the user wants to build"
    )
    required_nodes: list[str] = Field(
        description=(
            "List of n8n node type names needed "
            "(e.g. 'slack', 'telegram', 'webhook')"
        )
    )
    trigger_node: str = Field(
        default="webhook",
        description="The entry-point trigger node type (usually 'webhook')",
    )
    workflow_name: str = Field(
        description="Suggested name for the n8n workflow"
    )
