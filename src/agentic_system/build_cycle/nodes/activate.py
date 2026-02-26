"""Build Cycle Activate — activates the deployed workflow in n8n."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient
from src.api.settings import settings
from src.agentic_system.build_cycle.nodes._trigger_utils import extract_webhook_path


async def activate_node(state: ARIAState) -> dict:
    """Ensure workflow is active and return webhook URL.

    The test node already activates the workflow for testing.
    This node ensures it stays active and constructs the final URL.
    For non-webhook workflows, webhook_url is set to None.
    """
    workflow_id = state["n8n_workflow_id"]
    workflow_json = state["workflow_json"]

    client = N8nClient()
    await client.connect()
    try:
        await client.activate_workflow(workflow_id)
    except Exception:
        pass  # Already active from test phase
    finally:
        await client.disconnect()

    base = settings.n8n_base_url.rstrip("/")
    webhook_path = extract_webhook_path(workflow_json)
    has_webhook = any(
        "webhook" in node.get("type", "").lower()
        for node in workflow_json.get("nodes", [])
    )
    webhook_url = f"{base}/webhook/{webhook_path}" if has_webhook else None

    return {
        "webhook_url": webhook_url,
        "status": "done",
        "messages": [HumanMessage(
            content=f"[Activate] Workflow live! Webhook: {webhook_url or 'N/A'}"
        )],
    }
