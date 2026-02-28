"""Build Cycle Node Planner — LLM-driven flat DAG decomposition with cycle validation."""
from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, WorkflowTopology
from src.agentic_system.build_cycle.schemas.node_plan import NodePlan, PlannedEdge
from src.agentic_system.build_cycle.prompts.node_planner import NODE_PLANNER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.nodes._credential_resolver import resolve_node_credentials
from src.services.pipeline.event_bus import get_event_bus

logger = logging.getLogger(__name__)

MAX_CYCLE_RETRIES = 3

_agent = BaseAgent[NodePlan](
    prompt=NODE_PLANNER_SYSTEM_PROMPT,
    schema=NodePlan,
    name="NodePlanner",
)


async def node_planner_node(state: ARIAState) -> dict:
    """Decompose workflow topology into a flat NodeSpec list and planned edges."""
    bus = get_event_bus(state)
    if bus:
        await bus.emit_start("plan", "Node Planner", "Planning workflow nodes...")
    start = time.monotonic()

    blueprint = state.get("build_blueprint") or {}
    topology: WorkflowTopology | None = blueprint.get("topology")
    intent: str = blueprint.get("intent") or state.get("intent", "")
    cred_ids: dict = state.get("resolved_credential_ids", {})
    templates: list[dict] = state.get("node_templates", [])

    if not topology and not state.get("required_nodes"):
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete("plan", "Node Planner", "success", "No nodes to plan", duration_ms=elapsed)
        return _empty_plan()

    available_packages: list[str] = state.get("available_node_packages", [])
    prompt = _build_planner_prompt(intent, topology, cred_ids, templates, available_packages)
    plan = await _invoke_with_cycle_retry(prompt)

    if plan is None:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete("plan", "Node Planner", "error", "Cycle detected after retries", duration_ms=elapsed)
        logger.error("[NodePlanner] Cycle detected after %d retries — escalating", MAX_CYCLE_RETRIES)
        return _error_plan()

    elapsed = int((time.monotonic() - start) * 1000)
    if bus:
        await bus.emit_complete(
            "plan", "Node Planner", "success",
            f"Planned {len(plan.nodes)} nodes", duration_ms=elapsed,
        )
    return _plan_to_state_update(plan, cred_ids)


# ── LLM invocation with cycle-detection retry ──────────────────────────────────

async def _invoke_with_cycle_retry(base_prompt: str) -> NodePlan | None:
    """Invoke the LLM up to MAX_CYCLE_RETRIES times, feeding cycle errors back."""
    prompt = base_prompt
    for attempt in range(MAX_CYCLE_RETRIES):
        plan: NodePlan = await _agent.invoke([HumanMessage(content=prompt)])
        cycle_error = _detect_cycle(plan.edges)
        if cycle_error is None:
            return plan
        logger.warning("[NodePlanner] Cycle on attempt %d: %s", attempt + 1, cycle_error)
        prompt = _append_cycle_feedback(base_prompt, cycle_error)
    return None


def _append_cycle_feedback(base_prompt: str, cycle_error: str) -> str:
    """Extend the prompt with a cycle-detection error for the next retry."""
    return (
        base_prompt
        + f"\n\n## ERROR: Cycle detected in your previous answer\n{cycle_error}\n"
        + "Revise your edges so the graph is acyclic before responding again."
    )


# ── Cycle detection ────────────────────────────────────────────────────────────

def _detect_cycle(edges: list[PlannedEdge]) -> str | None:
    """Return an error message if a cycle exists; None if the graph is a valid DAG."""
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.from_node, []).append(edge.to_node)

    visited: set[str] = set()
    recursion_stack: set[str] = set()

    def has_cycle_from(node: str) -> bool:
        visited.add(node)
        recursion_stack.add(node)
        for neighbour in adjacency.get(node, []):
            if neighbour not in visited:
                if has_cycle_from(neighbour):
                    return True
            elif neighbour in recursion_stack:
                return True
        recursion_stack.discard(node)
        return False

    all_nodes = set(adjacency.keys()) | {n for neighbours in adjacency.values() for n in neighbours}
    for node in all_nodes:
        if node not in visited and has_cycle_from(node):
            return f"Cycle involving node '{node}' detected in edges."
    return None


# ── Prompt assembly ────────────────────────────────────────────────────────────

def _build_planner_prompt(
    intent: str,
    topology: WorkflowTopology | None,
    cred_ids: dict,
    templates: list[dict],
    available_packages: list[str] | None = None,
) -> str:
    sections = [f"## Intent\n{intent}"]

    if topology:
        sections.append(f"## Topology\n{json.dumps(topology, indent=2)}")
    else:
        sections.append("## Topology\n(none — infer a linear plan from intent)")

    sections.append(f"## Available credentials\n{json.dumps(cred_ids, indent=2)}")

    if available_packages:
        sections.append(
            f"## Available node packages (installed on this n8n instance)\n"
            f"{json.dumps(available_packages, indent=2)}\n"
            f"ONLY use node types from these packages. "
            f"Example: if 'n8n-nodes-base' is listed, you can use 'n8n-nodes-base.gmail', "
            f"'n8n-nodes-base.code', etc."
        )

    if templates:
        summaries = _summarise_templates(templates)
        sections.append(f"## RAG context (node template summaries)\n{summaries}")

    return "\n\n".join(sections)


def _summarise_templates(templates: list[dict]) -> str:
    """One-line summary per template — capped at 12 to avoid prompt bloat."""
    lines: list[str] = []
    for template in templates[:12]:
        node_type = template.get("node_type") or template.get("name", "unknown")
        doc = template.get("document", "")[:120].replace("\n", " ")
        lines.append(f"- {node_type}: {doc}")
    return "\n".join(lines)


# ── State conversion ───────────────────────────────────────────────────────────

def _plan_to_state_update(plan: NodePlan, resolved_credential_ids: dict) -> dict:
    nodes = [spec.model_dump() for spec in plan.nodes]
    resolve_node_credentials(nodes, resolved_credential_ids)
    node_names = ", ".join(spec.node_name for spec in plan.nodes)
    return {
        "nodes_to_build": nodes,
        "planned_edges": [edge.model_dump() for edge in plan.edges],
        "node_build_results": [],
        "messages": [HumanMessage(
            content=f"[Planner] {plan.overall_strategy} → {len(plan.nodes)} nodes queued: {node_names}"
        )],
    }


def _empty_plan() -> dict:
    return {
        "nodes_to_build": [],
        "planned_edges": [],
        "node_build_results": [],
        "messages": [HumanMessage(content="[Planner] No nodes to plan.")],
    }


def _error_plan() -> dict:
    return {
        "nodes_to_build": [],
        "planned_edges": [],
        "node_build_results": [],
        "status": "hitl_escalation",
        "messages": [HumanMessage(
            content="[Planner] Failed to produce a cycle-free plan after 3 retries. Escalating."
        )],
    }
