"""Build Cycle Phase Planner — LLM-driven topology decomposition."""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, PhaseEntry, WorkflowTopology
from src.agentic_system.build_cycle.schemas.phase_plan import PhasePlan
from src.agentic_system.build_cycle.prompts.phase_planner import (
    PHASE_PLANNER_SYSTEM_PROMPT,
)

_agent = BaseAgent[PhasePlan](
    prompt=PHASE_PLANNER_SYSTEM_PROMPT,
    schema=PhasePlan,
    name="PhasePlanner",
)


async def phase_planner_node(state: ARIAState) -> dict:
    """Use LLM to decompose workflow topology into ordered build phases."""
    blueprint = state.get("build_blueprint") or {}
    topology: WorkflowTopology | None = blueprint.get("topology")
    intent: str = blueprint.get("intent") or state.get("intent", "")
    cred_ids: dict = state.get("resolved_credential_ids", {})
    templates: list[dict] = state.get("node_templates", [])

    if not topology and not state.get("required_nodes"):
        return _empty_plan()

    prompt = _build_planner_prompt(intent, topology, cred_ids, templates)
    plan: PhasePlan = await _agent.invoke([HumanMessage(content=prompt)])

    phases = _plan_to_phase_entries(plan, topology)
    return {
        "phase_node_map": phases,
        "total_phases": len(phases),
        "build_phase": 0,
        "messages": [HumanMessage(
            content=(
                f"[Planner] {plan.overall_strategy} → "
                f"{len(phases)} phases: "
                + ", ".join(
                    f"[{', '.join(p.nodes)}]" for p in plan.phases
                )
            )
        )],
    }


# ── Prompt assembly ──────────────────────────────────────────────────────────

def _build_planner_prompt(
    intent: str,
    topology: WorkflowTopology | None,
    cred_ids: dict,
    templates: list[dict],
) -> str:
    sections = [f"## Intent\n{intent}"]

    if topology:
        sections.append(f"## Topology\n{json.dumps(topology, indent=2)}")
    else:
        sections.append("## Topology\n(none — fallback to linear plan)")

    sections.append(f"## Available credentials\n{json.dumps(cred_ids, indent=2)}")

    if templates:
        summaries = _summarise_templates(templates)
        sections.append(f"## RAG context (node template summaries)\n{summaries}")

    return "\n\n".join(sections)


def _summarise_templates(templates: list[dict]) -> str:
    """One-line summary per template to keep the prompt tight."""
    lines: list[str] = []
    for t in templates[:12]:  # cap at 12 to avoid prompt bloat
        node_type = t.get("node_type") or t.get("name", "unknown")
        doc = t.get("document", "")[:120].replace("\n", " ")
        lines.append(f"- {node_type}: {doc}")
    return "\n".join(lines)


# ── Plan → PhaseEntry conversion ─────────────────────────────────────────────

def _plan_to_phase_entries(
    plan: PhasePlan,
    topology: WorkflowTopology | None,
) -> list[PhaseEntry]:
    """Convert PhasePlan output to PhaseEntry list consumed by the engineer."""
    all_edges = topology.get("edges", []) if topology else []
    phase_entries: list[PhaseEntry] = []

    for i, phase in enumerate(plan.phases):
        bucket_set = set(phase.nodes)
        prev_buckets = {n for p in plan.phases[:i] for n in p.nodes}

        internal = [
            e for e in all_edges
            if e["from_node"] in bucket_set and e["to_node"] in bucket_set
        ]
        entry = [
            e for e in all_edges
            if e["from_node"] in prev_buckets and e["to_node"] in bucket_set
        ]
        phase_entries.append({
            "nodes": phase.nodes,
            "internal_edges": internal,
            "entry_edges": entry,
        })

    return phase_entries


def _empty_plan() -> dict:
    return {
        "phase_node_map": [],
        "total_phases": 0,
        "build_phase": 0,
        "messages": [HumanMessage(content="[Planner] No nodes to plan.")],
    }
