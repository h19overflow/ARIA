"""Build Cycle LangGraph subgraph -- RAG, plan, build, deploy, test, debug, activate."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.nodes.rag_retriever import rag_retriever_node
from src.agentic_system.build_cycle.nodes.phase_planner import phase_planner_node
from src.agentic_system.build_cycle.nodes.engineer import engineer_node
from src.agentic_system.build_cycle.nodes.deploy import deploy_node
from src.agentic_system.build_cycle.nodes.test import test_node
from src.agentic_system.build_cycle.nodes.debugger import debugger_node
from src.agentic_system.build_cycle.nodes.activate import activate_node
from src.agentic_system.build_cycle.nodes.hitl_escalation import (
    hitl_fix_escalation_node,
)

MAX_FIX_ATTEMPTS = 3
_FIXABLE_TYPES = {"schema", "logic"}


def _route_test_result(state: ARIAState) -> str:
    """Route based on execution result: next phase, activate, or debug."""
    result = state.get("execution_result")
    if result and result["status"] == "success":
        phase = state.get("build_phase", 0)
        total = state.get("total_phases", 1)
        if phase + 1 >= total:
            return "activate"
        return "advance_phase"
    return "debugger"


def _route_debugger_result(state: ARIAState) -> str:
    """Route after Debugger: re-deploy if fix was applied, else escalate."""
    error = state.get("classified_error")
    if not error:
        return "hitl_fix_escalation"

    error_type = error.get("type")
    has_budget = state.get("fix_attempts", 0) < MAX_FIX_ATTEMPTS

    if error_type == "rate_limit":
        return "test"  # retry the test without a code change
    if error_type in _FIXABLE_TYPES and has_budget and state.get("workflow_json"):
        return "deploy"  # fix was applied in debugger_node, redeploy
    return "hitl_fix_escalation"


def _route_hitl_decision(state: ARIAState) -> str:
    """Route after HITL escalation based on user's chosen action."""
    status = state.get("status", "failed")
    if status == "building":
        return "deploy"
    return "fail"


def _advance_phase(state: ARIAState) -> dict:
    """Increment build phase and reset per-phase state."""
    return {
        "build_phase": state.get("build_phase", 0) + 1,
        "fix_attempts": 0,
        "classified_error": None,
        "execution_result": None,
    }


def _mark_failed(state: ARIAState) -> dict:
    """Terminal node for unrecoverable errors."""
    if state.get("status") == "replanning":
        return {}
    return {"status": "failed"}


def build_build_cycle_graph() -> StateGraph:
    """Construct and return the Build Cycle subgraph."""
    graph = StateGraph(ARIAState)
    _register_nodes(graph)
    _wire_edges(graph)
    return graph


def _register_nodes(graph: StateGraph) -> None:
    graph.add_node("rag_retriever", rag_retriever_node)
    graph.add_node("phase_planner", phase_planner_node)
    graph.add_node("engineer", engineer_node)
    graph.add_node("deploy", deploy_node)
    graph.add_node("test", test_node)
    graph.add_node("debugger", debugger_node)
    graph.add_node("activate", activate_node)
    graph.add_node("hitl_fix_escalation", hitl_fix_escalation_node)
    graph.add_node("advance_phase", _advance_phase)
    graph.add_node("fail", _mark_failed)


def _wire_edges(graph: StateGraph) -> None:
    graph.set_entry_point("rag_retriever")
    graph.add_edge("rag_retriever", "phase_planner")
    graph.add_edge("phase_planner", "engineer")
    graph.add_edge("engineer", "deploy")
    graph.add_edge("deploy", "test")
    graph.add_edge("advance_phase", "engineer")
    graph.add_edge("activate", END)
    graph.add_edge("fail", END)

    graph.add_conditional_edges(
        "test",
        _route_test_result,
        {
            "activate": "activate",
            "advance_phase": "advance_phase",
            "debugger": "debugger",
        },
    )
    graph.add_conditional_edges(
        "debugger",
        _route_debugger_result,
        {
            "deploy": "deploy",
            "test": "test",
            "hitl_fix_escalation": "hitl_fix_escalation",
        },
    )
    graph.add_conditional_edges(
        "hitl_fix_escalation",
        _route_hitl_decision,
        {"deploy": "deploy", "fail": "fail"},
    )
