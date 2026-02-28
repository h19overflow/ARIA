"""Build Cycle Deploy — POST workflow to n8n."""
from __future__ import annotations

import httpx
from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient


async def deploy_node(state: ARIAState) -> dict:
    """Deploy workflow JSON to n8n, capture workflow ID."""
    workflow_json = state["workflow_json"]
    existing_id = state.get("n8n_workflow_id")

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
        return _handle_deploy_error(exc, workflow_json)
    finally:
        await client.disconnect()

    workflow_id = result["id"]
    return {
        "n8n_workflow_id": workflow_id,
        "status": "testing",
        "messages": [HumanMessage(content=f"[Deploy] Workflow deployed: {workflow_id}")],
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
        "status": "fixing",
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
