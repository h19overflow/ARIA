"""Build Cycle Deploy — POST workflow to n8n."""
from __future__ import annotations

import logging
import time

import httpx
from langchain_core.messages import HumanMessage

from src.api.settings import settings
from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient
from src.services.pipeline.event_bus import get_event_bus

log = logging.getLogger("aria.deploy")


def _validate_workflow_before_deploy(workflow_json: dict) -> str | None:
    """Pre-flight check before hitting the n8n API. Returns error message or None."""
    nodes = workflow_json.get("nodes", [])
    connections = workflow_json.get("connections", {})

    if not nodes:
        return "Workflow has no nodes"

    for node in nodes:
        if not node.get("id"):
            return f"Node '{node.get('name', '?')}' missing required 'id' field"
        if not node.get("type"):
            return f"Node '{node.get('name', '?')}' missing required 'type' field"

        node_type = node.get("type", "").lower()
        if "webhook" in node_type:
            if not node.get("webhookId"):
                return f"Webhook node '{node.get('name', '?')}' missing 'webhookId'"
            if not node.get("parameters", {}).get("path"):
                return f"Webhook node '{node.get('name', '?')}' missing 'parameters.path'"

    if len(nodes) > 1 and not connections:
        return f"Workflow has {len(nodes)} nodes but no connections"

    return None


async def deploy_node(state: ARIAState) -> dict:
    """Deploy workflow JSON to n8n, capture workflow ID."""
    bus = get_event_bus(state)
    if bus:
        await bus.emit_start("deploy", "Deploy", "Deploying workflow to n8n...")
    start = time.monotonic()

    workflow_json = state.get("workflow_json")
    existing_id = state.get("n8n_workflow_id")

    pre_deploy_error = _validate_workflow_before_deploy(workflow_json) if workflow_json else "workflow_json is None — assembler did not produce a valid workflow"
    if pre_deploy_error:
        log.warning("[Deploy] Pre-deploy validation failed: %s", pre_deploy_error)
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "deploy", "Deploy", "error",
                f"Pre-deploy validation: {pre_deploy_error}", duration_ms=elapsed,
            )
        return {
            "execution_result": {
                "status": "error", "execution_id": "", "data": None,
                "error": {
                    "type": None, "node_name": "unknown",
                    "message": pre_deploy_error,
                    "description": "Pre-deploy validation failure",
                    "line_number": None, "stack": None,
                },
            },
            "status": "failed",
            "messages": [HumanMessage(content=f"[Deploy] Validation failed: {pre_deploy_error}")],
        }

    # Strip read-only fields before sending to n8n API
    payload = {k: v for k, v in workflow_json.items() if k != "id"}

    client = N8nClient()
    await client.connect()
    try:
        if existing_id:
            result = await client.update_workflow(existing_id, payload)
        else:
            result = await client.deploy_workflow(payload)
    except httpx.HTTPStatusError as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "deploy", "Deploy", "error",
                f"Deploy failed: {exc}", duration_ms=elapsed,
            )
        return _handle_deploy_error(exc, workflow_json)
    finally:
        await client.disconnect()

    workflow_id = result["id"]
    elapsed = int((time.monotonic() - start) * 1000)
    if bus:
        await bus.emit_complete(
            "deploy", "Deploy", "success",
            f"Deployed workflow {workflow_id}", duration_ms=elapsed,
        )
    n8n_workflow_url = f"{settings.n8n_base_url.rstrip('/')}/workflow/{workflow_id}"
    return {
        "n8n_workflow_id": workflow_id,
        "n8n_workflow_url": n8n_workflow_url,
        "status": "done",
        "messages": [HumanMessage(content=f"[Deploy] Workflow created: {n8n_workflow_url}")],
    }


def _handle_deploy_error(
    exc: httpx.HTTPStatusError, workflow_json: dict,
) -> dict:
    """Parse n8n deploy error into execution_result for the debugger."""
    body = {}
    try:
        body = exc.response.json() if exc.response.content else {}
    except ValueError:
        pass

    error_msg = body.get("message", str(exc))
    node_name = _extract_node_name_from_error(body, error_msg, workflow_json)
    node_type = _extract_node_type_from_error(error_msg, workflow_json, node_name)

    description = f"Deploy failed with HTTP {exc.response.status_code}"
    if node_type:
        description += f". Node type: {node_type}"

    return {
        "execution_result": {
            "status": "error",
            "execution_id": "",
            "data": None,
            "error": {
                "type": None,
                "node_name": node_name,
                "message": error_msg,
                "description": description,
                "line_number": None,
                "stack": None,
            },
        },
        "status": "failed",
        "messages": [HumanMessage(content=f"[Deploy] Failed ({node_name}): {error_msg}")],
    }


def _extract_node_name_from_error(
    body: dict, error_msg: str, workflow_json: dict,
) -> str:
    """Try to extract the failing node name from n8n's error response."""
    # n8n sometimes includes context.nodeName
    node_name = body.get("context", {}).get("nodeName", "")
    if node_name:
        return node_name

    # Top-level nodeName (some n8n error shapes)
    node_name = body.get("nodeName", "")
    if node_name:
        return node_name

    # Scan workflow nodes — if error message mentions a node type, find its name
    for node in workflow_json.get("nodes", []):
        node_type = node.get("type", "")
        if node_type and node_type in error_msg:
            return node.get("name", node_type)

    return "unknown"


def _extract_node_type_from_error(
    error_msg: str, workflow_json: dict, node_name: str,
) -> str:
    """Extract the n8n node type string for better error reporting."""
    # If we found the node by name, return its type
    for node in workflow_json.get("nodes", []):
        if node.get("name") == node_name:
            return node.get("type", "")

    # Look for node type patterns in the error message
    for node in workflow_json.get("nodes", []):
        node_type = node.get("type", "")
        if node_type and node_type in error_msg:
            return node_type

    return ""
