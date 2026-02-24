"""Master ARIA graph -- chains Pre-Flight then Build Cycle."""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.preflight.graph import build_preflight_graph
from src.agentic_system.build_cycle.graph import build_build_cycle_graph


def build_aria_graph() -> StateGraph:
    """Construct the full ARIA pipeline graph."""
    preflight = build_preflight_graph().compile()
    build_cycle = build_build_cycle_graph().compile()

    graph = StateGraph(ARIAState)
    graph.add_node("preflight", preflight)
    graph.add_node("build_cycle", build_cycle)

    graph.set_entry_point("preflight")
    graph.add_edge("preflight", "build_cycle")
    graph.add_edge("build_cycle", END)

    return graph


def compile_aria_graph():
    """Build and compile the full ARIA graph, ready to invoke."""
    return build_aria_graph().compile()
