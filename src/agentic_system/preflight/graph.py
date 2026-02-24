"""Pre-Flight LangGraph subgraph -- intent parsing, credential resolution, blueprint."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agentic_system.shared.state import ARIAState, BuildBlueprint
from src.agentic_system.preflight.nodes.orchestrator import orchestrator_node
from src.agentic_system.preflight.nodes.credential_scanner import (
    credential_scanner_node,
)
from src.agentic_system.preflight.nodes.credential_guide import credential_guide_node
from src.agentic_system.preflight.nodes.credential_saver import (
    credential_saver_node,
)

MAX_CRED_RETRIES = 3


def _needs_credentials(state: ARIAState) -> str:
    """Route based on whether credentials are still pending."""
    if state.get("pending_credential_types"):
        return "credential_guide"
    return "handoff"


def _build_blueprint(state: ARIAState) -> dict:
    """Emit a BuildBlueprint from the resolved preflight state."""
    blueprint: BuildBlueprint = {
        "intent": state.get("intent_summary") or state.get("intent", ""),
        "required_nodes": state.get("required_nodes", []),
        "credential_ids": state.get("resolved_credential_ids", {}),
        "topology": state.get("topology") or {"nodes": [], "edges": [], "entry_node": "", "branch_nodes": []},
        "user_description": state.get("user_description", ""),
    }
    return {"build_blueprint": blueprint, "status": "building"}


def build_preflight_graph() -> StateGraph:
    """Construct and return the Pre-Flight subgraph."""
    graph = StateGraph(ARIAState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("credential_scanner", credential_scanner_node)
    graph.add_node("credential_guide", credential_guide_node)
    graph.add_node("credential_saver", credential_saver_node)
    graph.add_node("handoff", _build_blueprint)

    graph.set_entry_point("orchestrator")

    graph.add_edge("orchestrator", "credential_scanner")

    graph.add_conditional_edges(
        "credential_scanner",
        _needs_credentials,
        {
            "credential_guide": "credential_guide",
            "handoff": "handoff",
        },
    )

    graph.add_edge("credential_guide", "credential_saver")
    graph.add_edge("credential_saver", "credential_scanner")
    graph.add_edge("handoff", END)

    return graph
