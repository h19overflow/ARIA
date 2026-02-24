"""Pre-Flight Credential Saver — saves user-provided credentials to n8n."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient


async def credential_saver_node(state: ARIAState) -> dict:
    """Save pending credentials to n8n and return opaque IDs."""
    pending = state.get("pending_credential_types", [])
    resolved = dict(state.get("resolved_credential_ids", {}))

    if not pending:
        return {"pending_credential_types": [], "resolved_credential_ids": resolved}

    client = N8nClient()
    await client.connect()
    try:
        for cred_type in pending:
            # In production, user data comes from HITL interrupt
            # Here we create a placeholder that the demo can mock
            result = await client.save_credential(
                credential_type=cred_type,
                name=f"aria-{cred_type}",
                data={},
            )
            resolved[cred_type] = result["id"]
    finally:
        await client.disconnect()

    return {
        "resolved_credential_ids": resolved,
        "pending_credential_types": [],
        "messages": [HumanMessage(content=f"[Saver] Saved {len(pending)} credentials.")],
    }
