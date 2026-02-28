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
        return _handle_deploy_error(exc)
    finally:
        await client.disconnect()

    workflow_id = result["id"]
    return {
        "n8n_workflow_id": workflow_id,
        "status": "testing",
        "messages": [HumanMessage(content=f"[Deploy] Workflow deployed: {workflow_id}")],
    }


def _handle_deploy_error(exc: httpx.HTTPStatusError) -> dict:
    """Parse n8n deploy error into execution_result for the debugger."""
    body = {}
    try:
        body = exc.response.json() if exc.response.content else {}
    except ValueError:
        pass

    error_msg = body.get("message", str(exc))
    return {
        "execution_result": {
            "status": "error",
            "execution_id": "",
            "data": None,
            "error": {
                "type": None,
                "node_name": "unknown",
                "message": error_msg,
                "description": f"Deploy failed with HTTP {exc.response.status_code}",
                "line_number": None,
                "stack": None,
            },
        },
        "status": "fixing",
        "messages": [HumanMessage(content=f"[Deploy] Failed: {error_msg}")],
    }
