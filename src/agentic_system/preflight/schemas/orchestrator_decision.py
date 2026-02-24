"""Pydantic models for the Orchestrator's clarify/commit decision."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.agentic_system.preflight.schemas.blueprint import OrchestratorOutput


class ClarifyingQuestion(BaseModel):
    """A question the orchestrator wants to ask the user."""
    question: str = Field(description="The clarifying question to ask")
    reason: str = Field(description="Why this information is needed")


class OrchestratorDecision(BaseModel):
    """Orchestrator decides whether to clarify or commit."""
    decision: Literal["clarify", "commit"] = Field(
        description="'clarify' to ask the user a question, 'commit' to finalize the plan"
    )
    clarification: ClarifyingQuestion | None = Field(
        default=None,
        description="Required when decision='clarify'",
    )
    output: OrchestratorOutput | None = Field(
        default=None,
        description="Required when decision='commit'",
    )
