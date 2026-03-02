"""Node registration and edge wiring for the Build Cycle graph."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agentic_system.build_cycle.nodes.node_planner import node_planner_node
from src.agentic_system.build_cycle.nodes.node_worker import node_worker_node
from src.agentic_system.build_cycle.nodes.assembler import assembler_node
from src.agentic_system.build_cycle.nodes.deploy import deploy_node
from src.agentic_system.build_cycle.nodes.test import test_node
from src.agentic_system.build_cycle.nodes.debugger import debugger_node
from src.agentic_system.build_cycle.nodes.activate import activate_node
from src.agentic_system.build_cycle.nodes.hitl_escalation import (
    hitl_fix_escalation_node,
)
from src.agentic_system.build_cycle.nodes.modules._fan_out import fan_out_nodes
from src.agentic_system.build_cycle.nodes.modules._routers import (
    route_test_result,
    route_debugger_result,
    route_deploy_result,
    route_hitl_decision,
)
from src.agentic_system.shared.state import ARIAState


def mark_failed(state: ARIAState) -> dict:
    """Terminal node for unrecoverable errors."""
    if state.get("status") == "replanning":
        return {}
    return {"status": "failed"}


def register_nodes(graph: StateGraph) -> None:
    """Register all Build Cycle nodes on the graph."""
    graph.add_node("node_planner", node_planner_node)
    graph.add_node("node_worker", node_worker_node)
    graph.add_node("assembler", assembler_node)
    graph.add_node("deploy", deploy_node)
    graph.add_node("test", test_node)
    graph.add_node("debugger", debugger_node)
    graph.add_node("activate", activate_node)
    graph.add_node("hitl_fix_escalation", hitl_fix_escalation_node)
    graph.add_node("fail", mark_failed)


def wire_edges(graph: StateGraph) -> None:
    """Wire all edges and conditional routes on the graph."""
    graph.set_entry_point("node_planner")
    graph.add_conditional_edges("node_planner", fan_out_nodes, ["node_worker"])
    graph.add_edge("node_worker", "assembler")
    graph.add_edge("assembler", "deploy")
    graph.add_conditional_edges(
        "deploy",
        route_deploy_result,
        {"test": "test", "debugger": "debugger"},
    )
    graph.add_edge("activate", END)
    graph.add_edge("fail", END)

    graph.add_conditional_edges(
        "test",
        route_test_result,
        {"activate": "activate", "debugger": "debugger"},
    )
    graph.add_conditional_edges(
        "debugger",
        route_debugger_result,
        {"deploy": "deploy", "test": "test", "hitl_fix_escalation": "hitl_fix_escalation"},
    )
    graph.add_conditional_edges(
        "hitl_fix_escalation",
        route_hitl_decision,
        {"deploy": "deploy", "test": "test", "fail": "fail"},
    )
