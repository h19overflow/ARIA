"""Node Substituter — replaces unavailable nodes with built-in alternatives."""
from __future__ import annotations

import json
import logging
import time
import uuid

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.schemas.node_plan import SubstitutionResult
from src.agentic_system.build_cycle.prompts.node_substituter import (
    NODE_SUBSTITUTER_SYSTEM_PROMPT,
)
from src.services.pipeline.event_bus import get_event_bus

logger = logging.getLogger(__name__)

_agent = BaseAgent[SubstitutionResult](
    prompt=NODE_SUBSTITUTER_SYSTEM_PROMPT,
    schema=SubstitutionResult,
    name="NodeSubstituter",
)


async def node_substituter_node(state: ARIAState) -> dict:
    """Attempt to replace an unavailable node with built-in alternatives."""
    bus = get_event_bus(state)
    error = state.get("classified_error") or {}
    node_name = error.get("node_name", "unknown")

    if bus:
        await bus.emit_start("fix", "Node Substituter", f"Substituting {node_name}...")
    start = time.monotonic()

    workflow_json = state.get("workflow_json")

    if not workflow_json:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "fix", "Node Substituter", "error",
                "No workflow JSON available", duration_ms=elapsed,
            )
        return _escalate("No workflow JSON available for substitution.")

    failing_node = _find_failing_node(workflow_json, node_name)
    if not failing_node:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "fix", "Node Substituter", "error",
                f"Node '{node_name}' not found", duration_ms=elapsed,
            )
        return _escalate(
            f"Could not find node '{error.get('node_name')}' in workflow."
        )

    prompt = _build_substituter_prompt(failing_node, error, state)
    result: SubstitutionResult = await _agent.invoke(
        [HumanMessage(content=prompt)]
    )

    if not result.substitution_possible:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "fix", "Node Substituter", "error",
                f"Cannot substitute: {result.reason}", duration_ms=elapsed,
            )
        return _escalate(result.reason, error=error)

    updated_workflow = _apply_substitution(workflow_json, result)
    elapsed = int((time.monotonic() - start) * 1000)
    if bus:
        await bus.emit_complete(
            "fix", "Node Substituter", "success",
            f"Replaced '{result.removed_node_name}' with {len(result.replacement_nodes)} node(s)",
            duration_ms=elapsed,
        )
    return {
        "workflow_json": updated_workflow,
        "classified_error": None,
        "status": "building",
        "messages": [
            HumanMessage(
                content=(
                    f"[Substituter] Replaced '{result.removed_node_name}' with "
                    f"{len(result.replacement_nodes)} built-in node(s): "
                    f"{result.reason}"
                )
            )
        ],
    }


def _find_failing_node(workflow_json: dict, node_name: str) -> dict | None:
    """Find the node dict in workflow_json by name."""
    for node in workflow_json.get("nodes", []):
        if node.get("name") == node_name:
            return node
    return None


def _build_substituter_prompt(
    failing_node: dict,
    error: dict,
    state: ARIAState,
) -> str:
    """Assemble the prompt for the substituter agent."""
    available = state.get("available_node_packages", ["n8n-nodes-base"])
    compact_node = _summarize_node(failing_node)
    compact_error = {
        "type": error.get("type"),
        "node_name": error.get("node_name"),
        "message": error.get("message"),
        "description": error.get("description"),
    }
    return "\n\n".join([
        f"## Failing node\n{json.dumps(compact_node, indent=2)}",
        f"## Error\n{json.dumps(compact_error, indent=2)}",
        f"## Available packages\n{json.dumps(available, indent=2)}",
        "## Task\nReplace this node with n8n-nodes-base alternatives.",
    ])


def _summarize_node(node: dict) -> dict:
    """Extract only the fields the substituter needs — drop large parameters."""
    summary: dict = {
        "name": node.get("name"),
        "type": node.get("type"),
        "typeVersion": node.get("typeVersion"),
    }
    if node.get("credentials"):
        summary["credentials"] = node["credentials"]

    parameters = node.get("parameters", {})
    # Include parameter keys and short scalar values so the LLM understands
    # the node's intent, but truncate large nested blobs.
    compact_params: dict = {}
    for key, value in parameters.items():
        if isinstance(value, str) and len(value) > 300:
            compact_params[key] = value[:300] + "...(truncated)"
        elif isinstance(value, (dict, list)):
            serialized = json.dumps(value)
            if len(serialized) > 300:
                compact_params[key] = f"<{type(value).__name__} with {len(serialized)} chars>"
            else:
                compact_params[key] = value
        else:
            compact_params[key] = value
    summary["parameters"] = compact_params
    return summary


def _apply_substitution(
    workflow_json: dict, result: SubstitutionResult
) -> dict:
    """Replace the failing node in workflow_json with the substitution nodes."""
    patched = dict(workflow_json)
    old_nodes = list(patched.get("nodes", []))
    new_nodes = []

    for node in old_nodes:
        if node.get("name") == result.removed_node_name:
            for replacement in result.replacement_nodes:
                new_node = {
                    "id": str(uuid.uuid4()),
                    "name": replacement.name,
                    "type": replacement.type,
                    "typeVersion": 1,
                    "position": node.get("position", [0, 0]),
                    "parameters": replacement.parameters,
                }
                if node.get("credentials"):
                    new_node["credentials"] = node["credentials"]
                new_nodes.append(new_node)
        else:
            new_nodes.append(node)

    patched["nodes"] = new_nodes
    return patched


def _escalate(reason: str, *, error: dict | None = None) -> dict:
    """Return state update that routes to HITL escalation."""
    return {
        "classified_error": error or {
            "type": "missing_node",
            "node_name": "unknown",
            "message": reason,
            "description": None,
            "line_number": None,
            "stack": None,
        },
        "status": "fixing",
        "messages": [
            HumanMessage(
                content=(
                    f"[Substituter] Cannot substitute: {reason}. "
                    "Escalating to user."
                )
            )
        ],
    }
