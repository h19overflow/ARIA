"""Pre-Flight Credential Saver -- interrupts for user credentials, saves to n8n."""
from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient


async def credential_saver_node(state: ARIAState) -> dict:
    """Interrupt for credentials, save them to n8n, update resolved IDs."""
    pending = state.get("pending_credential_types", [])
    resolved = dict(state.get("resolved_credential_ids", {}))

    if not pending:
        return {
            "pending_credential_types": [],
            "resolved_credential_ids": resolved,
            "paused_for_input": False,
        }

    guide = state.get("credential_guide_payload") or {}

    response: dict = interrupt({
        "type": "credential_request",
        "pending_types": pending,
        "paused_for_input": True,
        **guide,
    })

    action = response.get("action", "resume") if isinstance(response, dict) else "resume"
    user_creds: dict[str, dict] = response.get("credentials", {}) if action == "provide" else {}

    if user_creds:
        client = N8nClient()
        await client.connect()
        try:
            for cred_type, cred_data in user_creds.items():
                result = await client.save_credential(cred_type, cred_type, cred_data)
                resolved[cred_type] = result["id"]
        finally:
            await client.disconnect()

    saved_types = list(user_creds.keys())
    remaining = [p for p in pending if p not in saved_types]

    return {
        "resolved_credential_ids": resolved,
        "pending_credential_types": remaining,
        "paused_for_input": False,
        "messages": [HumanMessage(
            content=f"[Saver] Saved credentials for: {', '.join(saved_types) or 'none (resumed from n8n)'}",
        )],
    }
