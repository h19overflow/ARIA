"""Build Cycle Engineer -- assembles workflow JSON from templates + blueprint."""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, PhaseEntry
from src.agentic_system.build_cycle.schemas.workflow import EngineerOutput
from src.agentic_system.build_cycle.prompts.engineer import ENGINEER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.nodes._engineer_helpers import (
    to_n8n_payload,
    merge_into_existing,
)


_agent = BaseAgent[EngineerOutput](
    prompt=ENGINEER_SYSTEM_PROMPT,
    schema=EngineerOutput,
    name="Engineer",
)


async def engineer_node(state: ARIAState) -> dict:
    """Use LLM to build or extend an n8n workflow for the current phase."""
    blueprint = state["build_blueprint"]
    templates = state.get("node_templates", [])
    cred_ids = state.get("resolved_credential_ids", {})
    phase = state.get("build_phase", 0)
    phase_map = state.get("phase_node_map", [])
    existing_workflow = state.get("workflow_json")

    phase_entry: PhaseEntry = phase_map[phase] if phase < len(phase_map) else {"nodes": [], "internal_edges": [], "entry_edges": []}
    phase_nodes = phase_entry["nodes"]
    phase_templates = _filter_templates(templates, phase_nodes)

    prompt = _build_phase_prompt(
        blueprint, phase_templates, cred_ids, phase, phase_entry, existing_workflow,
    )
    result: EngineerOutput = await _agent.invoke([HumanMessage(content=prompt)])

    workflow_json = to_n8n_payload(result, cred_ids)
    if existing_workflow and phase > 0:
        workflow_json = merge_into_existing(existing_workflow, workflow_json)

    return {
        "workflow_json": workflow_json,
        "status": "building",
        "messages": [HumanMessage(
            content=f"[Engineer] Phase {phase}: built {len(result.nodes)} nodes ({', '.join(phase_nodes)})."
        )],
    }


def _filter_templates(templates: list[dict], phase_nodes: list[str]) -> list[dict]:
    """Return only templates matching current phase's node types."""
    phase_set = {n.lower() for n in phase_nodes}
    return [t for t in templates if _template_matches(t, phase_set)]


def _template_matches(template: dict, phase_set: set[str]) -> bool:
    """Check if a template matches any node in the current phase."""
    name = template.get("node_type", template.get("name", "")).lower()
    return any(p in name for p in phase_set)


def _build_phase_prompt(
    blueprint: dict,
    templates: list[dict],
    cred_ids: dict[str, str],
    phase: int,
    phase_entry: PhaseEntry,
    existing_workflow: dict | None,
) -> str:
    """Build the human message for the engineer, phase-aware."""
    phase_nodes = phase_entry["nodes"]
    base = (
        f"Intent: {blueprint.get('intent', '')}\n"
        f"Phase: {phase}\n"
        f"Nodes to add in this phase: {phase_nodes}\n"
        f"Credential IDs: {json.dumps(cred_ids)}\n"
        f"Node templates:\n{json.dumps(templates, indent=2)}"
    )
    if existing_workflow and phase > 0:
        base += (
            f"\n\nExisting workflow (DO NOT recreate these nodes, only ADD new ones):\n"
            f"{json.dumps(existing_workflow, indent=2)}"
        )
    base += _build_topology_block(phase, phase_entry)
    return base


def _build_topology_block(phase: int, phase_entry: PhaseEntry) -> str:
    """Build the topology section appended to the engineer prompt."""
    internal_edges = phase_entry["internal_edges"]
    entry_edges = phase_entry["entry_edges"]

    if not internal_edges and not entry_edges:
        return ""

    lines = [f"\n\n## Phase {phase} Connection Map", f"Nodes to build: {phase_entry['nodes']}"]

    if internal_edges:
        lines.append("\nConnections within this phase:")
        for edge in internal_edges:
            branch = edge["branch"] or "main"
            lines.append(f"  {edge['from_node']} --[{branch}]--> {edge['to_node']}")

    if entry_edges:
        lines.append("\nEntry connections from previous phase:")
        for edge in entry_edges:
            branch = edge["branch"] or "main"
            lines.append(f"  {edge['from_node']} (EXISTING) --[{branch}]--> {edge['to_node']} (NEW)")
            lines.append(f"  \u2191 Connect {edge['to_node']} to the existing node named \"{edge['from_node']}\"")

    return "\n".join(lines)
