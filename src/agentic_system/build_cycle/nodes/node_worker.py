"""Parallel node worker — builds one n8n node JSON from a NodeSpec via Send API."""
from __future__ import annotations

import json
import time
import uuid

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.build_cycle.prompts.node_worker import NODE_WORKER_SYSTEM_PROMPT
from src.services.pipeline.event_bus import get_event_bus

_HORIZONTAL_SPACING_PX = 250
_DEFAULT_Y_POSITION = 300


class WorkerOutput(BaseModel):
    """LLM output for a single n8n node."""

    parameters: dict = Field(description="Complete n8n node parameters")
    type_version: int = Field(default=1, description="Node type version")


_agent = BaseAgent[WorkerOutput](
    prompt=NODE_WORKER_SYSTEM_PROMPT,
    schema=WorkerOutput,
    name="NodeWorker",
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
        templates: list[dict] = state.get("node_templates", [])
        cred_ids: dict = state.get("resolved_credential_ids", {})

        relevant_templates = _filter_templates_for_node(templates, node_spec.get("node_type", ""))
        prompt = _build_worker_prompt(node_spec, relevant_templates, cred_ids)

        output: WorkerOutput = await _agent.invoke([HumanMessage(content=prompt)])
        node_json = _assemble_node_json(node_spec, output)

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

def _build_worker_prompt(node_spec: dict, templates: list[dict], cred_ids: dict) -> str:
    """Assemble the human message for the node worker."""
    sections = [
        f"## Node to build\n{json.dumps(node_spec, indent=2)}",
        f"## Resolved credential IDs\n{json.dumps(cred_ids, indent=2)}",
    ]
    if templates:
        sections.append(f"## RAG templates (reference only)\n{json.dumps(templates, indent=2)}")
    return "\n\n".join(sections)


# ── Node JSON assembly ────────────────────────────────────────────────────────

def _assemble_node_json(node_spec: dict, output: WorkerOutput) -> dict:
    """Combine NodeSpec metadata with LLM-generated parameters into full n8n node."""
    node: dict = {
        "id": str(uuid.uuid4()),
        "name": node_spec["node_name"],
        "type": node_spec["node_type"],
        "typeVersion": output.type_version,
        "position": _calculate_position(node_spec.get("position_index", 0)),
        "parameters": output.parameters,
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


# ── Template filtering ────────────────────────────────────────────────────────

def _filter_templates_for_node(templates: list[dict], node_type: str) -> list[dict]:
    """Return RAG templates relevant to this specific node type."""
    node_type_lower = node_type.lower()
    return [
        t for t in templates
        if node_type_lower in (t.get("node_type", "") or t.get("name", "")).lower()
    ]


# ── Result constructors ───────────────────────────────────────────────────────

def _success_result(node_name: str, node_json: dict) -> dict:
    """Build a passing NodeResult."""
    return {
        "node_name": node_name,
        "node_json": node_json,
        "validation_passed": True,
        "validation_errors": [],
    }


def _failure_result(node_name: str, exc: Exception) -> dict:
    """Build a failing NodeResult from an exception."""
    return {
        "node_name": node_name,
        "node_json": {},
        "validation_passed": False,
        "validation_errors": [f"{type(exc).__name__}: {exc}"],
    }
