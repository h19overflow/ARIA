"""Build Cycle Activate — activates the deployed workflow in n8n."""
from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient
from src.api.settings import settings
from src.agentic_system.build_cycle.nodes._trigger_utils import (
    detect_trigger_type,
    extract_webhook_path,
)
from src.services.pipeline.event_bus import get_event_bus

log = logging.getLogger("aria.activate")


async def activate_node(state: ARIAState) -> dict:
    """Ensure workflow is active and return webhook URL.

    The test node already activates the workflow for testing.
    This node ensures it stays active and constructs the final URL.
    For non-webhook workflows, webhook_url is set to None.
    """
    bus = get_event_bus(state)
    if bus:
        await bus.emit_start("activate", "Activate", "Activating workflow...")
    start = time.monotonic()

    workflow_id = state["n8n_workflow_id"]
    workflow_json = state["workflow_json"]

    client = N8nClient()
    await client.connect()
    try:
        await client.activate_workflow(workflow_id)
    except Exception as exc:
        log.warning(
            "Activation attempt failed (may already be active): %s", exc, exc_info=True
        )
    finally:
        await client.disconnect()

    base = settings.n8n_base_url.rstrip("/")
    is_webhook = detect_trigger_type(workflow_json) == "webhook"
    webhook_path = extract_webhook_path(workflow_json) if is_webhook else None
    webhook_url = f"{base}/webhook/{webhook_path}" if is_webhook else None

    elapsed = int((time.monotonic() - start) * 1000)
    if bus:
        await bus.emit_complete(
            "activate", "Activate", "success",
            f"Workflow activated: {webhook_url or 'N/A'}", duration_ms=elapsed,
        )

    return {
        "webhook_url": webhook_url,
        "status": "done",
        "messages": [HumanMessage(
            content=f"[Activate] Workflow live! Webhook: {webhook_url or 'N/A'}"
        )],
    }
