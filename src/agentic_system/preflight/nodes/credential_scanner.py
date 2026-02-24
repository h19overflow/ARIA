"""Pre-Flight Credential Scanner — diffs required vs saved credentials."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.shared.node_credential_map import get_credential_types
from src.boundary.n8n.client import N8nClient


async def credential_scanner_node(state: ARIAState) -> dict:
    """Diff required node credential types against saved n8n credentials."""
    required_nodes = state["required_nodes"]

    client = N8nClient()
    await client.connect()
    try:
        saved = await client.list_credentials()
    finally:
        await client.disconnect()

    saved_by_type = _group_credentials_by_type(saved)
    resolved, pending = _resolve_credentials(required_nodes, saved_by_type)

    messages = []
    if pending:
        messages.append(HumanMessage(
            content=f"[Scanner] Missing credentials for: {', '.join(pending)}"
        ))
    else:
        messages.append(HumanMessage(content="[Scanner] All credentials resolved."))

    return {
        "resolved_credential_ids": resolved,
        "pending_credential_types": pending,
        "messages": messages,
    }


def _group_credentials_by_type(credentials: list[dict]) -> dict[str, list[dict]]:
    """Group saved credentials by their type field."""
    grouped: dict[str, list[dict]] = {}
    for cred in credentials:
        cred_type = cred.get("type", "")
        grouped.setdefault(cred_type, []).append(cred)
    return grouped


def _resolve_credentials(
    required_nodes: list[str],
    saved_by_type: dict[str, list[dict]],
) -> tuple[dict[str, str], list[str]]:
    """Match required nodes to saved credentials. Returns (resolved, pending)."""
    resolved: dict[str, str] = {}
    pending: list[str] = []

    for node_type in required_nodes:
        cred_types = get_credential_types(node_type)
        if not cred_types:
            continue  # Node needs no credential

        found = False
        for cred_type in cred_types:
            candidates = saved_by_type.get(cred_type, [])
            if len(candidates) == 1:
                resolved[cred_type] = candidates[0]["id"]
                found = True
                break
            elif len(candidates) > 1:
                # Pick first for now (HITL would ask user in production)
                resolved[cred_type] = candidates[0]["id"]
                found = True
                break

        if not found:
            pending.append(cred_types[0])  # Request first option

    return resolved, pending
