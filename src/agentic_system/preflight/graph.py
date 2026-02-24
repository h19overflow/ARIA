"""Pre-Flight LangGraph subgraph -- intent parsing, credential resolution, blueprint."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agentic_system.shared.state import ARIAState, BuildBlueprint
from src.agentic_system.preflight.nodes.orchestrator import orchestrator_node
from src.agentic_system.preflight.nodes.hitl_clarify import (
    hitl_clarify_node,
    MAX_ORCHESTRATOR_TURNS,
)
from src.agentic_system.preflight.nodes.credential_scanner import (
    credential_scanner_node,
)
from src.agentic_system.preflight.nodes.credential_saver import (
    credential_saver_node,
)

MAX_CRED_RETRIES = 3


def _route_orchestrator_decision(state: ARIAState) -> str:
    """Route based on orchestrator's clarify/commit decision."""
    decision = state.get("orchestrator_decision", "commit")
    turns = state.get("orchestrator_turns", 0)
    if decision == "clarify" and turns < MAX_ORCHESTRATOR_TURNS:
        return "hitl_clarify"
    return "credential_scanner"


def _needs_credentials(state: ARIAState) -> str:
    """Route based on whether credentials are still pending."""
    if state.get("pending_credential_types"):
        return "credential_saver"
    return "handoff"


def _build_blueprint(state: ARIAState) -> dict:
    """Emit a BuildBlueprint from the resolved preflight state."""
    blueprint: BuildBlueprint = {
        "intent": state.get("intent", ""),
        "required_nodes": state.get("required_nodes", []),
        "credential_ids": state.get("resolved_credential_ids", {}),
        "topology": state.get("topology", {"nodes": [], "edges": [], "entry_node": "", "branch_nodes": []}),
        "user_description": state.get("user_description", ""),
    }
    return {"build_blueprint": blueprint, "status": "building"}


def build_preflight_graph() -> StateGraph:
    """Construct and return the Pre-Flight subgraph."""
    graph = StateGraph(ARIAState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("hitl_clarify", hitl_clarify_node)
    graph.add_node("credential_scanner", credential_scanner_node)
    graph.add_node("credential_saver", credential_saver_node)
    graph.add_node("handoff", _build_blueprint)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        _route_orchestrator_decision,
        {
            "hitl_clarify": "hitl_clarify",
            "credential_scanner": "credential_scanner",
        },
    )

    graph.add_edge("hitl_clarify", "orchestrator")

    graph.add_conditional_edges(
        "credential_scanner",
        _needs_credentials,
        {
            "credential_saver": "credential_saver",
            "handoff": "handoff",
        },
    )

    graph.add_edge("credential_saver", "credential_scanner")
    graph.add_edge("handoff", END)

    return graph
