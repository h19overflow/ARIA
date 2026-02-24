"""Output schema for the Phase Planner agent."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlannedPhase(BaseModel):
    """One build phase produced by the planner agent."""

    nodes: list[str] = Field(
        description=(
            "Ordered list of node names to build in this phase. "
            "Names must exactly match the topology node names."
        )
    )
    rationale: str = Field(
        description=(
            "One sentence explaining why these nodes are grouped together "
            "(e.g. 'trigger + auth share the same credential context')."
        )
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "Node names from PREVIOUS phases that this phase connects to. "
            "Empty for phase 0."
        ),
    )


class PhasePlan(BaseModel):
    """Complete ordered build plan returned by the Phase Planner agent."""

    phases: list[PlannedPhase] = Field(
        description="Ordered list of build phases, from trigger to final action."
    )
    overall_strategy: str = Field(
        description=(
            "One sentence summarising the decomposition strategy chosen "
            "(e.g. 'credential boundary split' or 'linear pipeline')."
        )
    )
