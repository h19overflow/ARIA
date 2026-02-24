"""Pre-Flight Credential Scanner — diffs required vs saved credentials."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.agentic_system.shared.node_credential_map import get_credential_types
from src.boundary.n8n.client import N8nClient


async def credential_scanner_node(state: ARIAState) -> dict:
    """Diff required node credential types against saved n8n credentials.

    Merges with already-resolved IDs from state so the saver loop terminates.
    """
    required_nodes = state["required_nodes"]
    already_resolved = dict(state.get("resolved_credential_ids", {}))

    client = N8nClient()
    await client.connect()
    try:
        saved = await client.list_credentials()
    finally:
        await client.disconnect()

    saved_by_type = _group_credentials_by_type(saved)
    resolved, pending = _resolve_credentials(
        required_nodes, saved_by_type, already_resolved,
    )

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
    already_resolved: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Match required nodes to saved credentials. Returns (resolved, pending).

    Skips credential types that are already in already_resolved (from prior saver runs).
    """
    resolved: dict[str, str] = dict(already_resolved)
    pending: list[str] = []

    for node_type in required_nodes:
        cred_types = get_credential_types(node_type)
        if not cred_types:
            continue  # Node needs no credential

        # Skip if any credential type for this node is already resolved
        if any(ct in resolved for ct in cred_types):
            continue

        found = False
        for cred_type in cred_types:
            candidates = saved_by_type.get(cred_type, [])
            if candidates:
                resolved[cred_type] = candidates[0]["id"]
                found = True
                break

        if not found:
            pending.append(cred_types[0])  # Request first option

    return resolved, pending
