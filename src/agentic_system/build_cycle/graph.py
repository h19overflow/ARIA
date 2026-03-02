"""Build Cycle LangGraph subgraph -- plan, build, deploy, test, debug, activate."""
from __future__ import annotations

from langgraph.graph import StateGraph

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.nodes.modules._graph_wiring import (
    register_nodes,
    wire_edges,
)


def build_build_cycle_graph() -> StateGraph:
    """Construct and return the Build Cycle subgraph."""
    graph = StateGraph(ARIAState)
    register_nodes(graph)
    wire_edges(graph)
    return graph
