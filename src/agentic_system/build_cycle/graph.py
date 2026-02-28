"""Build Cycle LangGraph subgraph -- plan, build, deploy, test, debug, activate."""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.types import Send

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.nodes.node_planner import node_planner_node
from src.agentic_system.build_cycle.nodes.node_worker import node_worker_node
from src.agentic_system.build_cycle.nodes.assembler import assembler_node
from src.agentic_system.build_cycle.nodes.deploy import deploy_node
from src.agentic_system.build_cycle.nodes.test import test_node
from src.agentic_system.build_cycle.nodes.debugger import debugger_node
from src.agentic_system.build_cycle.nodes.activate import activate_node
from src.agentic_system.build_cycle.nodes.node_substituter import node_substituter_node
from src.agentic_system.build_cycle.nodes.hitl_escalation import (
    hitl_fix_escalation_node,
)

MAX_FIX_ATTEMPTS = 3
_FIXABLE_TYPES = {"schema", "logic"}


def fan_out_nodes(state: ARIAState) -> list[Send]:
    """Fan out NodeSpec list to parallel workers via Send API."""
    nodes_to_build = state.get("nodes_to_build", [])
    if not nodes_to_build:
        return []
    return [
        Send("node_worker", {
            "node_spec": spec,
            "resolved_credential_ids": state.get("resolved_credential_ids", {}),
            "job_id": state.get("job_id", ""),
        })
        for spec in nodes_to_build
    ]


def _route_test_result(state: ARIAState) -> str:
    """Route based on execution result: activate on success or debug on failure."""
    result = state.get("execution_result")
    if result and result["status"] == "success":
        return "activate"
    return "debugger"


def _route_debugger_result(state: ARIAState) -> str:
    """Route after Debugger: re-deploy if fix was applied, else escalate."""
    error = state.get("classified_error")
    if not error:
        return "hitl_fix_escalation"

    error_type = error.get("type")
    has_budget = state.get("fix_attempts", 0) < MAX_FIX_ATTEMPTS

    if error_type == "missing_node" and has_budget:
        return "node_substituter"
    if error_type == "rate_limit":
        return "test"
    if error_type in _FIXABLE_TYPES and has_budget and state.get("workflow_json"):
        return "deploy"
    if error_type == "auth" and has_budget and state.get("workflow_json"):
        return "deploy"
    return "hitl_fix_escalation"


def _route_deploy_result(state: ARIAState) -> str:
    """Route after deploy: test on success, debugger on failure."""
    if state.get("status") == "fixing":
        return "debugger"
    return "test"


def _route_substituter_result(state: ARIAState) -> str:
    """Route after substitution: deploy if fixed, escalate if not."""
    if state.get("status") == "building" and state.get("workflow_json"):
        return "deploy"
    return "hitl_fix_escalation"


def _route_hitl_decision(state: ARIAState) -> str:
    """Route after HITL escalation based on user's chosen action."""
    status = state.get("status", "failed")
    if status == "building":
        return "deploy"
    if status == "testing":
        return "test"
    return "fail"


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
    graph.add_node("node_planner", node_planner_node)
    graph.add_node("node_worker", node_worker_node)
    graph.add_node("assembler", assembler_node)
    graph.add_node("deploy", deploy_node)
    graph.add_node("test", test_node)
    graph.add_node("debugger", debugger_node)
    graph.add_node("activate", activate_node)
    graph.add_node("node_substituter", node_substituter_node)
    graph.add_node("hitl_fix_escalation", hitl_fix_escalation_node)
    graph.add_node("fail", _mark_failed)


def _wire_edges(graph: StateGraph) -> None:
    graph.set_entry_point("node_planner")
    graph.add_conditional_edges("node_planner", fan_out_nodes, ["node_worker"])
    graph.add_edge("node_worker", "assembler")
    graph.add_edge("assembler", "deploy")
    graph.add_conditional_edges(
        "deploy",
        _route_deploy_result,
        {"test": "test", "debugger": "debugger"},
    )
    graph.add_edge("activate", END)
    graph.add_edge("fail", END)

    graph.add_conditional_edges(
        "test",
        _route_test_result,
        {
            "activate": "activate",
            "debugger": "debugger",
        },
    )
    graph.add_conditional_edges(
        "debugger",
        _route_debugger_result,
        {
            "deploy": "deploy",
            "test": "test",
            "node_substituter": "node_substituter",
            "hitl_fix_escalation": "hitl_fix_escalation",
        },
    )
    graph.add_conditional_edges(
        "node_substituter",
        _route_substituter_result,
        {"deploy": "deploy", "hitl_fix_escalation": "hitl_fix_escalation"},
    )
    graph.add_conditional_edges(
        "hitl_fix_escalation",
        _route_hitl_decision,
        {"deploy": "deploy", "test": "test", "fail": "fail"},
    )
