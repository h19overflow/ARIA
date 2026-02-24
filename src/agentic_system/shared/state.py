"""Central LangGraph state shared across preflight and build_cycle."""
from __future__ import annotations
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class WorkflowEdge(TypedDict):
    """A directed edge between two workflow nodes."""
    from_node: str        # matches a name in WorkflowTopology.nodes
    to_node: str
    branch: str | None    # "true"/"false" for If; "1"/"2" for Switch; None = linear


class WorkflowTopology(TypedDict):
    """Directed graph of the workflow produced during preflight."""
    nodes: list[str]              # display-ordered node names
    edges: list[WorkflowEdge]
    entry_node: str               # trigger node (always phase 0)
    branch_nodes: list[str]       # nodes with multiple outbound edges (If, Switch)


class PhaseEntry(TypedDict):
    """One build phase with topology context for the Engineer."""
    nodes: list[str]                    # node names to build this phase
    internal_edges: list[WorkflowEdge]  # edges entirely within this phase
    entry_edges: list[WorkflowEdge]     # edges crossing in FROM the previous phase


class BuildBlueprint(TypedDict):
    """Handoff contract from Pre-Flight → Build Cycle."""
    intent: str
    required_nodes: list[str]        # kept for rag_retriever compat
    credential_ids: dict[str, str]
    topology: WorkflowTopology       # NEW
    user_description: str            # NEW


class ClassifiedError(TypedDict):
    """Output of the Error Classifier node."""
    type: str  # "schema" | "auth" | "rate_limit" | "logic"
    node_name: str
    message: str
    description: str | None
    line_number: int | None
    stack: str | None


class ExecutionResult(TypedDict):
    """Parsed result from an n8n execution poll."""
    status: str  # "success" | "error"
    execution_id: str
    data: dict | None
    error: ClassifiedError | None


class ARIAState(TypedDict):
    """Master state for the full ARIA LangGraph pipeline."""
    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Pre-Flight owned
    intent: str
    required_nodes: list[str]
    resolved_credential_ids: dict[str, str]
    pending_credential_types: list[str]
    credential_guide_payload: dict | None
    build_blueprint: BuildBlueprint | None

    # Topology (written by orchestrator on commit, copied into build_blueprint by handoff)
    topology: WorkflowTopology | None
    user_description: str

    # Written by orchestrator on commit
    intent_summary: str

    # Conversational orchestrator
    orchestrator_decision: str  # "clarify" | "commit"
    pending_question: str
    orchestrator_turns: int

    # Build Cycle owned
    node_templates: list[dict]
    workflow_json: dict | None
    n8n_workflow_id: str | None
    n8n_execution_id: str | None
    execution_result: ExecutionResult | None
    classified_error: ClassifiedError | None
    fix_attempts: int
    webhook_url: str | None
    status: str  # "planning" | "building" | "testing" | "fixing" | "done" | "failed" | "replanning"

    # Incremental build phases
    build_phase: int
    total_phases: int
    phase_node_map: list[PhaseEntry]
