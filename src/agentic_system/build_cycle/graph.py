"""Build Cycle LangGraph subgraph -- RAG, build, deploy, test, fix, activate."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.nodes.rag_retriever import rag_retriever_node
from src.agentic_system.build_cycle.nodes.engineer import engineer_node
from src.agentic_system.build_cycle.nodes.deploy import deploy_node
from src.agentic_system.build_cycle.nodes.test import test_node
from src.agentic_system.build_cycle.nodes.error_classifier import (
    error_classifier_node,
)
from src.agentic_system.build_cycle.nodes.fix import fix_node
from src.agentic_system.build_cycle.nodes.activate import activate_node

MAX_FIX_ATTEMPTS = 3


def _route_test_result(state: ARIAState) -> str:
    """Route based on execution result status."""
    result = state.get("execution_result")
    if result and result["status"] == "success":
        return "activate"
    return "error_classifier"


def _route_error_type(state: ARIAState) -> str:
    """Route based on classified error type and remaining fix budget."""
    error = state.get("classified_error")
    if not error:
        return "fail"

    is_fixable = error["type"] in ("schema",)
    has_budget = state.get("fix_attempts", 0) < MAX_FIX_ATTEMPTS

    if is_fixable and has_budget:
        return "fix"
    if error["type"] == "rate_limit":
        return "test"  # retry the execution
    return "fail"


def _mark_failed(state: ARIAState) -> dict:
    """Terminal node for unrecoverable errors."""
    return {"status": "failed"}


def build_build_cycle_graph() -> StateGraph:
    """Construct and return the Build Cycle subgraph."""
    graph = StateGraph(ARIAState)

    graph.add_node("rag_retriever", rag_retriever_node)
    graph.add_node("engineer", engineer_node)
    graph.add_node("deploy", deploy_node)
    graph.add_node("test", test_node)
    graph.add_node("error_classifier", error_classifier_node)
    graph.add_node("fix", fix_node)
    graph.add_node("activate", activate_node)
    graph.add_node("fail", _mark_failed)

    graph.set_entry_point("rag_retriever")
    graph.add_edge("rag_retriever", "engineer")
    graph.add_edge("engineer", "deploy")
    graph.add_edge("deploy", "test")

    graph.add_conditional_edges(
        "test",
        _route_test_result,
        {"activate": "activate", "error_classifier": "error_classifier"},
    )

    graph.add_conditional_edges(
        "error_classifier",
        _route_error_type,
        {"fix": "fix", "test": "test", "fail": "fail"},
    )

    # Re-deploy after a fix attempt
    graph.add_edge("fix", "deploy")
    graph.add_edge("activate", END)
    graph.add_edge("fail", END)

    return graph
