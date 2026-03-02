"""Parallel node worker — builds one n8n node JSON from a NodeSpec via Send API."""
from __future__ import annotations

import json
import time
import uuid

from langchain_core.messages import AIMessage, HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.build_cycle.prompts.node_worker import NODE_WORKER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.tools import search_n8n_nodes
from src.services.pipeline.event_bus import get_event_bus
from src.agentic_system.build_cycle.nodes.modules._node_worker_helpers import (
    extract_parameters_from_response,
    _validate_node_output,
    _success_result,
    _failure_result,
)

_HORIZONTAL_SPACING_PX = 250
_DEFAULT_Y_POSITION = 300
_TRIGGER_TYPES = {"n8n-nodes-base.webhook", "n8n-nodes-base.scheduletrigger", "n8n-nodes-base.cron"}

# NOTE: No schema= here. Gemini's structured output mode (response_format)
# causes it to return empty parameters {}. Without it, Gemini correctly
# populates parameters from search results and prompt hints.
_agent = BaseAgent(
    prompt=NODE_WORKER_SYSTEM_PROMPT,
    name="NodeWorker",
    tools=[search_n8n_nodes],
    recursion_limit=20,
)


async def node_worker_node(state: dict) -> dict:
    """Build one n8n node JSON from the NodeSpec in state and return a NodeResult."""
    bus = get_event_bus(state)
    node_spec: dict = state.get("node_spec", {})
    node_name = node_spec.get("node_name", "unknown")

    if bus:
        await bus.emit_start("build", node_name, f"Building {node_name}...")
    start = time.monotonic()

    try:
        cred_ids: dict = state.get("resolved_credential_ids", {})
        prompt = _build_worker_prompt(node_spec, cred_ids)

        ai_message: AIMessage = await _agent.invoke([HumanMessage(content=prompt)])
        parameters = extract_parameters_from_response(ai_message, node_spec)
        node_json = _assemble_node_json(node_spec, parameters)

        validation_errors = _validate_node_output(node_json)
        if validation_errors:
            elapsed = int((time.monotonic() - start) * 1000)
            if bus:
                await bus.emit_complete(
                    "build", node_name, "error",
                    f"{node_name} validation failed: {validation_errors[0]}", duration_ms=elapsed,
                )
            return {"node_build_results": [_failure_result(node_name, validation_errors)]}

        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "build", node_name, "success",
                f"{node_name} built successfully", duration_ms=elapsed,
            )
        return {"node_build_results": [_success_result(node_spec["node_name"], node_json)]}

    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "build", node_name, "error",
                f"{node_name} failed: {exc}", duration_ms=elapsed,
            )
        return {"node_build_results": [_failure_result(node_name, exc)]}


# ── Prompt assembly ───────────────────────────────────────────────────────────

def _build_worker_prompt(node_spec: dict, cred_ids: dict) -> str:
    """Assemble the human message for the node worker."""
    sections = [
        f"## Node to build\n{json.dumps(node_spec, indent=2)}",
        f"## Resolved credential IDs\n{json.dumps(cred_ids, indent=2)}",
    ]
    return "\n\n".join(sections)


# ── Node JSON assembly ────────────────────────────────────────────────────────

def _assemble_node_json(node_spec: dict, parameters: dict) -> dict:
    """Combine NodeSpec metadata with LLM-generated parameters into full n8n node."""
    node: dict = {
        "id": str(uuid.uuid4()),
        "name": node_spec["node_name"],
        "type": node_spec["node_type"],
        "typeVersion": 1,
        "position": _calculate_position(node_spec.get("position_index", 0)),
        "parameters": parameters,
    }
    _attach_webhook_id_if_needed(node)
    _attach_credentials_if_present(node, node_spec)
    return node


def _calculate_position(position_index: int) -> list[int]:
    """Calculate canvas position from the node's sequential index."""
    return [position_index * _HORIZONTAL_SPACING_PX, _DEFAULT_Y_POSITION]


def _attach_webhook_id_if_needed(node: dict) -> None:
    """Add a webhookId UUID for webhook-type nodes."""
    if "webhook" in node["type"].lower():
        node["webhookId"] = str(uuid.uuid4())


def _attach_credentials_if_present(node: dict, node_spec: dict) -> None:
    """Wire credential reference from NodeSpec into the node JSON."""
    credential_id = node_spec.get("credential_id")
    credential_type = node_spec.get("credential_type")
    if credential_id and credential_type:
        node["credentials"] = {
            credential_type: {"id": credential_id, "name": credential_type}
        }
