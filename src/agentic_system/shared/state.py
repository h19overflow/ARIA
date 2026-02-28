"""Central LangGraph state shared across preflight and build_cycle."""
from __future__ import annotations
import operator
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


class BuildBlueprint(TypedDict):
    """Handoff contract from Pre-Flight → Build Cycle."""
    intent: str
    required_nodes: list[str]        # used by node_planner for topology hints
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

    # Preflight context — set by Phase 1 agent and carried into build cycle
    intent: str
    required_nodes: list[str]
    resolved_credential_ids: dict[str, str]
    pending_credential_types: list[str]
    credential_guide_payload: dict | None
    build_blueprint: BuildBlueprint | None

    # Topology — seeded as empty stub by build adapter, populated by phase_planner
    topology: WorkflowTopology | None
    user_description: str

    # Written by orchestrator on commit
    intent_summary: str

    # Conversational orchestrator
    conversation_notes: dict | None

    # Build Cycle owned
    workflow_json: dict | None
    n8n_workflow_id: str | None
    n8n_execution_id: str | None
    execution_result: ExecutionResult | None
    classified_error: ClassifiedError | None
    fix_attempts: int
    webhook_url: str | None
    status: str  # "planning" | "building" | "testing" | "fixing" | "done" | "failed" | "replanning"

    # Node availability — populated by node_planner
    available_node_packages: list[str]

    # Parallel build — fan-out/fan-in via LangGraph Send
    nodes_to_build: list                                 # NodeSpec dicts from planner; replaced on each write
    planned_edges: list                                  # all edges from planner (no reducer needed)
    node_build_results: Annotated[list, operator.add]   # NodeResult dicts aggregated from parallel workers

    # HITL pause indicator — set True immediately before interrupt(), False after resume.
    # Frontend can read this without inferring from SSE gaps.
    paused_for_input: bool

    # LLM-generated explanation shown to the user during a HITL pause.
    hitl_explanation: str | None

    # Job identifier — used by EventBus to publish SSE events from nodes
    job_id: str

    # Conversational orchestrator internal fields
    orchestrator_decision: str
    pending_question: str
    orchestrator_turns: int
