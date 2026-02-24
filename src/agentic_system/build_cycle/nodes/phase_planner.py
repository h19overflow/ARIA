"""Build Cycle Phase Planner -- splits workflow topology into ordered build phases."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState, WorkflowTopology, PhaseEntry

LOGIC_NODES = {"if", "switch", "merge", "set", "code", "splitInBatches", "noOp"}
_MAX_LOGIC_PER_PHASE = 2


async def phase_planner_node(state: ARIAState) -> dict:
    """Split workflow topology into ordered build phases."""
    blueprint = state.get("build_blueprint") or {}
    topology = blueprint.get("topology")

    if topology:
        phases = _build_phases_from_topology(topology)
    else:
        required = state.get("required_nodes", [])
        if not required:
            return _empty_plan()
        phases = _fallback_phases(required)

    return {
        "phase_node_map": phases,
        "total_phases": len(phases),
        "build_phase": 0,
        "messages": [HumanMessage(
            content=f"[Planner] Split into {len(phases)} phases."
        )],
    }


def _build_phases_from_topology(topology: WorkflowTopology) -> list[PhaseEntry]:
    """BFS walk of topology edges → ordered list of PhaseEntry."""
    phase_buckets = _bfs_assign_phases(topology)
    return _attach_edges(phase_buckets, topology)


def _bfs_assign_phases(topology: WorkflowTopology) -> list[list[str]]:
    """BFS from entry_node, assign each node to a phase bucket respecting density limits."""
    edges = topology.get("edges", [])
    adj: dict[str, list[str]] = {}
    for edge in edges:
        adj.setdefault(edge["from_node"], []).append(edge["to_node"])

    entry = topology["entry_node"]
    phases: list[list[str]] = [[entry]]
    visited: set[str] = {entry}
    queue: list[str] = list(adj.get(entry, []))
    current_phase: list[str] = []
    logic_count = 0

    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)

        if _is_logic_node(node):
            current_phase.append(node)
            logic_count += 1
            if logic_count >= _MAX_LOGIC_PER_PHASE:
                phases.append(current_phase)
                current_phase = []
                logic_count = 0
        else:
            if current_phase:
                phases.append(current_phase)
                current_phase = []
                logic_count = 0
            phases.append([node])

        queue.extend(n for n in adj.get(node, []) if n not in visited)

    if current_phase:
        phases.append(current_phase)

    return phases


def _attach_edges(
    phase_buckets: list[list[str]], topology: WorkflowTopology
) -> list[PhaseEntry]:
    """For each phase bucket, split edges into internal vs entry (cross-phase)."""
    all_edges = topology.get("edges", [])
    result: list[PhaseEntry] = []

    for i, bucket in enumerate(phase_buckets):
        bucket_set = set(bucket)
        prev_set = set(phase_buckets[i - 1]) if i > 0 else set()
        internal = [
            e for e in all_edges
            if e["from_node"] in bucket_set and e["to_node"] in bucket_set
        ]
        entry = [
            e for e in all_edges
            if e["from_node"] in prev_set and e["to_node"] in bucket_set
        ]
        result.append({"nodes": bucket, "internal_edges": internal, "entry_edges": entry})

    return result


def _fallback_phases(required_nodes: list[str]) -> list[PhaseEntry]:
    """Backward compat: flat list → PhaseEntry list with no edge data."""
    trigger = required_nodes[0]
    phases: list[PhaseEntry] = [{"nodes": [trigger], "internal_edges": [], "entry_edges": []}]
    for node in required_nodes[1:]:
        phases.append({"nodes": [node], "internal_edges": [], "entry_edges": []})
    return phases


def _is_logic_node(node_type: str) -> bool:
    """Check if a node type is logic-only (no credentials)."""
    return node_type.lower() in LOGIC_NODES


def _empty_plan() -> dict:
    """Return empty phase plan."""
    return {
        "phase_node_map": [],
        "total_phases": 0,
        "build_phase": 0,
        "messages": [HumanMessage(content="[Planner] No nodes to plan.")],
    }
