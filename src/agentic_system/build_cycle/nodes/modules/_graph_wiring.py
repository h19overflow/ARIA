"""Node registration and edge wiring for the Build Cycle graph."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agentic_system.build_cycle.nodes.node_planner import node_planner_node
from src.agentic_system.build_cycle.nodes.node_worker import node_worker_node
from src.agentic_system.build_cycle.nodes.assembler import assembler_node
from src.agentic_system.build_cycle.nodes.deploy import deploy_node
from src.agentic_system.build_cycle.nodes.modules._fan_out import fan_out_nodes


def register_nodes(graph: StateGraph) -> None:
    """Register all Build Cycle nodes on the graph."""
    graph.add_node("node_planner", node_planner_node)
    graph.add_node("node_worker", node_worker_node)
    graph.add_node("assembler", assembler_node)
    graph.add_node("deploy", deploy_node)


def wire_edges(graph: StateGraph) -> None:
    """Wire all edges: planner -> workers -> assembler -> deploy -> END."""
    graph.set_entry_point("node_planner")
    graph.add_conditional_edges("node_planner", fan_out_nodes, ["node_worker"])
    graph.add_edge("node_worker", "assembler")
    graph.add_edge("assembler", "deploy")
    graph.add_edge("deploy", END)
