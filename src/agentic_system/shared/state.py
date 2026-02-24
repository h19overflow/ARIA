"""Central LangGraph state shared across preflight and build_cycle."""
from __future__ import annotations
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class BuildBlueprint(TypedDict):
    """Handoff contract from Pre-Flight → Build Cycle."""
    intent: str
    required_nodes: list[str]
    credential_ids: dict[str, str]  # credential_type → opaque n8n ID


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
    build_blueprint: BuildBlueprint | None

    # Build Cycle owned
    node_templates: list[dict]
    workflow_json: dict | None
    n8n_workflow_id: str | None
    n8n_execution_id: str | None
    execution_result: ExecutionResult | None
    classified_error: ClassifiedError | None
    fix_attempts: int
    webhook_url: str | None
    status: str  # "planning" | "building" | "testing" | "fixing" | "done" | "failed"
