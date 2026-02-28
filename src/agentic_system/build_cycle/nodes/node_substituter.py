"""Node Substituter — replaces unavailable nodes with built-in alternatives."""
from __future__ import annotations

import json
import uuid
import logging

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.schemas.node_plan import SubstitutionResult
from src.agentic_system.build_cycle.prompts.node_substituter import (
    NODE_SUBSTITUTER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

_agent = BaseAgent[SubstitutionResult](
    prompt=NODE_SUBSTITUTER_SYSTEM_PROMPT,
    schema=SubstitutionResult,
    name="NodeSubstituter",
)


async def node_substituter_node(state: ARIAState) -> dict:
    """Attempt to replace an unavailable node with built-in alternatives."""
    error = state.get("classified_error") or {}
    workflow_json = state.get("workflow_json")

    if not workflow_json:
        return _escalate("No workflow JSON available for substitution.")

    failing_node = _find_failing_node(workflow_json, error.get("node_name", ""))
    if not failing_node:
        return _escalate(
            f"Could not find node '{error.get('node_name')}' in workflow."
        )

    prompt = _build_substituter_prompt(failing_node, error, state)
    result: SubstitutionResult = await _agent.invoke(
        [HumanMessage(content=prompt)]
    )

    if not result.substitution_possible:
        return _escalate(result.reason, error=error)

    updated_workflow = _apply_substitution(workflow_json, result)
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
    return "\n\n".join([
        f"## Failing node\n{json.dumps(failing_node, indent=2)}",
        f"## Error\n{json.dumps(error, indent=2)}",
        f"## Available packages\n{json.dumps(available, indent=2)}",
        "## Task\nReplace this node with n8n-nodes-base alternatives.",
    ])


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
                    "typeVersion": replacement.type_version,
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
