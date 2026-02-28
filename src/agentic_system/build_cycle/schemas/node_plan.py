"""Schemas for the parallel node fan-out build pipeline."""
from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field


class PlannedEdge(BaseModel):
    """A directed connection between two nodes in the workflow plan."""

    from_node: str = Field(description="Source node name")
    to_node: str = Field(description="Target node name")
    branch: str | None = Field(
        default=None,
        description=(
            "Branch label for conditional nodes. "
            "'true'/'false' for If nodes; '1'/'2' for Switch nodes; "
            "None for linear connections."
        ),
    )


class NodeSpec(BaseModel):
    """Input to a parallel worker — describes a single n8n node to build."""

    node_name: str = Field(description="Display name of the node (e.g. 'Send Email')")
    node_type: str = Field(
        description="n8n node type identifier (e.g. 'n8n-nodes-base.gmail')"
    )
    parameter_hints: dict = Field(
        default_factory=dict,
        description="Planner-supplied hints and overrides for node parameters",
    )
    credential_id: str | None = Field(
        default=None,
        description="Resolved n8n credential ID if this node requires authentication",
    )
    credential_type: str | None = Field(
        default=None,
        description="Credential type name (e.g. 'gmailOAuth2Api')",
    )
    position_index: int = Field(
        description="Ordering hint used to compute canvas layout position"
    )


class NodePlan(BaseModel):
    """LLM structured output from the node planner — full parallel build plan."""

    nodes: list[NodeSpec] = Field(
        description="All nodes to build in parallel, one per worker"
    )
    edges: list[PlannedEdge] = Field(
        description="All directed connections between nodes"
    )
    workflow_name: str = Field(description="Display name for the assembled workflow")
    overall_strategy: str = Field(
        description=(
            "One sentence explaining the decomposition strategy chosen "
            "(e.g. 'linear trigger → enrichment → notification pipeline')."
        )
    )


class NodeResult(TypedDict):
    """Output returned by a parallel node worker after building one node."""

    node_name: str
    node_json: dict
    validation_passed: bool
    validation_errors: list[str]


class ReplacementNode(BaseModel):
    """A single replacement node produced by the substituter."""

    name: str = Field(description="Node display name")
    type: str = Field(description="n8n node type (must be n8n-nodes-base.*)")
    type_version: int = Field(default=1, description="Node type version")
    parameters: dict = Field(description="Complete n8n node parameters")


class SubstitutionResult(BaseModel):
    """Output from the Node Substituter agent."""

    substitution_possible: bool = Field(
        description="Whether a built-in replacement exists"
    )
    reason: str = Field(description="Why substitution is or isn't possible")
    replacement_nodes: list[ReplacementNode] = Field(
        default_factory=list,
        description="Replacement node(s) using only n8n-nodes-base types",
    )
    removed_node_name: str = Field(
        description="Name of the node being replaced"
    )
