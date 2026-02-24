"""Build Cycle Deploy — POST workflow to n8n."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient


async def deploy_node(state: ARIAState) -> dict:
    """Deploy workflow JSON to n8n, capture workflow ID."""
    workflow_json = state["workflow_json"]
    existing_id = state.get("n8n_workflow_id")

    client = N8nClient()
    await client.connect()
    try:
        if existing_id:
            result = await client.update_workflow(existing_id, workflow_json)
        else:
            result = await client.deploy_workflow(workflow_json)
    finally:
        await client.disconnect()

    workflow_id = result["id"]
    return {
        "n8n_workflow_id": workflow_id,
        "status": "testing",
        "messages": [HumanMessage(content=f"[Deploy] Workflow deployed: {workflow_id}")],
    }
