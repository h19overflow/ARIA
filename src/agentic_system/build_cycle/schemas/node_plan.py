"""Schemas for the parallel node fan-out build pipeline."""
from __future__ import annotations

import json
from typing import Any, TypedDict, Optional

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("parameter_hints", mode="before")
    @classmethod
    def coerce_json_string_to_dict(cls, v: Any) -> dict:
        """Auto-coerce JSON strings to dicts — prevents LLM retry spirals."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            return {}
        return v if isinstance(v, dict) else {}


class NodePlan(BaseModel):
    """LLM structured output from the node planner — full parallel build plan."""

    nodes: list[NodeSpec] = Field(
        description="All nodes to build in parallel, one per worker"
    )
    edges: list[PlannedEdge] = Field(
        description="All directed connections between nodes"
    )
    workflow_name: str = Field(description="Display name for the assembled workflow")


class NodeResult(TypedDict):
    """Output returned by a parallel node worker after building one node."""

    node_name: str
    node_json: dict
    validation_passed: bool
    validation_errors: list[str]



class WorkerOutput(BaseModel):
    """LLM output for a single n8n node worker."""
    parameters: dict = Field(description="Complete n8n node parameters")


class ConnectionTarget(BaseModel):
    """A single connection target on one output port."""
    node: str = Field(description="Target node name (exact match)")
    type: str = Field(default="main", description="Connection type, always 'main'")
    index: int = Field(default=0, description="Input port on target node, usually 0")


class SourceNodeConnections(BaseModel):
    """All outgoing connections from one source node — keyed by source name."""
    source_node_name: str = Field(
        description="Exact name of the source node (must match a name from node_list)"
    )
    main: list[list[ConnectionTarget]] = Field(
        description=(
            "Output ports list. main[0] is output 0, main[1] is output 1, etc. "
            "Each port contains a list of connection targets. "
            "For If nodes: main[0]=true branch, main[1]=false branch. "
            "For linear edges: use main[0] only."
        ),
    )


class AssemblerOutput(BaseModel):
    """LLM output from the Assembler agent — complete n8n connections object."""
    connections: list[SourceNodeConnections] = Field(
        description=(
            "One entry per source node that has outgoing edges. "
            "Every edge from planned_edges MUST appear here."
        ),
    )


class SearchInput(BaseModel):
    """Input for n8n node search tool."""
    query: str = Field(description="Search terms for node types")
    doc_type: Optional[str] = Field(default="node", description="node | workflow_template")
    n_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return (1-20). Use more for broad/ambiguous queries.",
    )
