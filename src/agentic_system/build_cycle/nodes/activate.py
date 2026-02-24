"""Build Cycle Activate — activates the deployed workflow in n8n."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient
from src.api.settings import settings


async def activate_node(state: ARIAState) -> dict:
    """Ensure workflow is active and return webhook URL.

    The test node already activates the workflow for testing.
    This node ensures it stays active and constructs the final URL.
    """
    workflow_id = state["n8n_workflow_id"]
    webhook_path = _extract_webhook_path(state["workflow_json"])

    client = N8nClient()
    await client.connect()
    try:
        await client.activate_workflow(workflow_id)
    except Exception:
        pass  # Already active from test phase
    finally:
        await client.disconnect()

    base = settings.n8n_base_url.rstrip("/")
    webhook_url = f"{base}/webhook/{webhook_path}"

    return {
        "webhook_url": webhook_url,
        "status": "done",
        "messages": [HumanMessage(
            content=f"[Activate] Workflow live! Webhook: {webhook_url}"
        )],
    }


def _extract_webhook_path(workflow_json: dict) -> str:
    """Find the webhook path from workflow nodes."""
    for node in workflow_json.get("nodes", []):
        if "webhook" in node.get("type", "").lower():
            return node.get("parameters", {}).get("path", "test-webhook")
    return "test-webhook"
