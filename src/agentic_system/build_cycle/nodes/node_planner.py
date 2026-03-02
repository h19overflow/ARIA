"""Build Cycle Node Planner — two-phase: Researcher (RAG) + Composer (structured output)."""
from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, WorkflowTopology
from src.agentic_system.build_cycle.schemas.node_plan import NodePlan, PlannedEdge
from src.agentic_system.build_cycle.prompts.node_researcher import NODE_RESEARCHER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.prompts.plan_composer import PLAN_COMPOSER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.nodes.modules._credential_resolver import resolve_node_credentials
from src.agentic_system.build_cycle.tools import search_n8n_nodes
from src.boundary.n8n.node_discovery import discover_installed_node_prefixes
from src.services.pipeline.event_bus import get_event_bus

logger = logging.getLogger(__name__)

MAX_CYCLE_RETRIES = 3

# Phase 1: Tool-use agent, text output — searches ChromaDB for node docs
_researcher = BaseAgent(
    prompt=NODE_RESEARCHER_SYSTEM_PROMPT,
    schema=None,
    name="NodeResearcher",
    tools=[search_n8n_nodes],
    recursion_limit=30,
)

# Phase 2: Structured output agent, no tools — composes the NodePlan
_composer = BaseAgent[NodePlan](
    prompt=PLAN_COMPOSER_SYSTEM_PROMPT,
    schema=NodePlan,
    name="PlanComposer",
    tools=[],
    recursion_limit=5,
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

    if not topology and not state.get("required_nodes"):
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete("plan", "Node Planner", "success", "No nodes to plan", duration_ms=elapsed)
        return _empty_plan()

    available_packages = await discover_installed_node_prefixes()
    sorted_packages = sorted(available_packages)

    # Phase 1: Researcher searches for node documentation
    catalog = await _run_researcher(intent, topology, cred_ids, sorted_packages)

    # Phase 2: Composer produces the structured NodePlan
    plan = await _run_composer_with_cycle_retry(catalog, intent, cred_ids, sorted_packages)

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
    return _plan_to_state_update(plan, cred_ids, sorted_packages)


# ── Phase 1: Researcher ──────────────────────────────────────────────────────

async def _run_researcher(
    intent: str,
    topology: WorkflowTopology | None,
    cred_ids: dict,
    available_packages: list[str],
) -> str:
    """Run the Researcher agent to produce a node catalog via RAG search."""
    prompt = _build_researcher_prompt(intent, topology, cred_ids, available_packages)
    result: AIMessage = await _researcher.invoke([HumanMessage(content=prompt)])
    logger.info("[NodeResearcher] Catalog produced (%d chars)", len(result.content))
    return result.content


# ── Phase 2: Composer with cycle-detection retry ─────────────────────────────

async def _run_composer_with_cycle_retry(
    catalog: str,
    intent: str,
    cred_ids: dict,
    available_packages: list[str],
) -> NodePlan | None:
    """Run the Composer agent up to MAX_CYCLE_RETRIES times."""
    base_prompt = _build_composer_prompt(catalog, intent, cred_ids, available_packages)
    prompt = base_prompt

    for attempt in range(MAX_CYCLE_RETRIES):
        plan: NodePlan = await _composer.invoke([HumanMessage(content=prompt)])
        
        errors = []
        cycle_error = _detect_cycle(plan.edges)
        if cycle_error:
            errors.append(cycle_error)
            
        unknown_nodes_error = _detect_unknown_nodes(plan.nodes, available_packages)
        if unknown_nodes_error:
            errors.append(unknown_nodes_error)
            
        if not errors:
            return plan
            
        error_msg = "\n\n".join(errors)
        logger.warning("[PlanComposer] Validation error on attempt %d: %s", attempt + 1, error_msg)
        prompt = base_prompt + (
            f"\n\n## ERROR: Validation failed for your previous answer\n{error_msg}\n"
            "Revise your node plan to fix these issues before responding again."
        )
    return None

# ── Validation ────────────────────────────────────────────────────────────────

def _detect_unknown_nodes(nodes: list, available_packages: list[str]) -> str | None:
    """Check if any planned node uses a package prefix that isn't installed."""
    if not available_packages:
        return None
        
    invalid_nodes = []
    for node in nodes:
        node_type = node.node_type
        if "." not in node_type:
            if node_type not in available_packages:
                invalid_nodes.append(node_type)
        else:
            prefix = node_type.rsplit(".", 1)[0]
            if prefix not in available_packages:
                invalid_nodes.append(node_type)
                
    if invalid_nodes:
        invalid_str = ", ".join(invalid_nodes)
        return (
            f"The following node types belong to packages that are NOT installed: {invalid_str}.\n"
            "You MUST replace them with valid nodes from the 'Available node packages' list (e.g. fallback to 'n8n-nodes-base.httpRequest' or 'n8n-nodes-base.code')."
        )
    return None


# ── Cycle detection ───────────────────────────────────────────────────────────

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


# ── Prompt assembly ───────────────────────────────────────────────────────────

def _build_researcher_prompt(
    intent: str,
    topology: WorkflowTopology | None,
    cred_ids: dict,
    available_packages: list[str],
) -> str:
    """Build the human message for the Researcher agent."""
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
            f"You MUST ONLY search for node types from these packages."
        )

    return "\n\n".join(sections)


def _build_composer_prompt(
    catalog: str,
    intent: str,
    cred_ids: dict,
    available_packages: list[str],
) -> str:
    """Build the human message for the Composer agent."""
    sections = [
        f"## Node Catalog (from Researcher — use ONLY these nodes)\n{catalog}",
        f"## Intent\n{intent}",
        f"## Available credentials\n{json.dumps(cred_ids, indent=2)}",
    ]

    if available_packages:
        sections.append(
            f"## Available node packages\n{json.dumps(available_packages, indent=2)}"
        )

    return "\n\n".join(sections)


# ── State conversion ─────────────────────────────────────────────────────────

def _plan_to_state_update(plan: NodePlan, resolved_credential_ids: dict, available_packages: list[str]) -> dict:
    nodes = [spec.model_dump() for spec in plan.nodes]
    resolve_node_credentials(nodes, resolved_credential_ids)
    node_names = ", ".join(spec.node_name for spec in plan.nodes)
    return {
        "nodes_to_build": nodes,
        "planned_edges": [edge.model_dump() for edge in plan.edges],
        "node_build_results": [],
        "available_node_packages": available_packages,
        "messages": [HumanMessage(
            content=f"[Planner] '{plan.workflow_name}' → {len(plan.nodes)} nodes queued: {node_names}"
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
        "status": "failed",
        "messages": [HumanMessage(
            content="[Planner] Failed to produce a cycle-free plan after 3 retries. Escalating."
        )],
    }
