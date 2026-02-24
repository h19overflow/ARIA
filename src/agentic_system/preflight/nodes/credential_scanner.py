"""Pre-Flight Credential Scanner — diffs required vs saved credentials."""
from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

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
    resolved, pending, ambiguous = _resolve_credentials(
        required_nodes, saved_by_type, already_resolved,
    )

    # HITL: ask user to pick when multiple credentials of the same type exist.
    if ambiguous:
        choices: dict[str, str] = interrupt({
            "type": "credential_ambiguity",
            "ambiguous": {
                cred_type: [{"id": c["id"], "name": c.get("name", c["id"])} for c in candidates]
                for cred_type, candidates in ambiguous.items()
            },
            "message": (
                "Multiple saved credentials found. "
                "Please choose one ID per type."
            ),
        })
        # choices: {cred_type: credential_id}
        for cred_type, cred_id in choices.items():
            resolved[cred_type] = cred_id

    messages = []
    if pending:
        messages.append(HumanMessage(
            content=f"[Scanner] Missing credentials for: {', '.join(pending)}"
        ))
    elif ambiguous:
        messages.append(HumanMessage(
            content=f"[Scanner] Ambiguous credentials for: {', '.join(ambiguous)}"
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
) -> tuple[dict[str, str], list[str], dict[str, list[dict]]]:
    """Match required nodes to saved credentials.

    Returns (resolved, pending, ambiguous):
    - resolved: cred_type -> id (single match or already resolved)
    - pending: cred_types with no saved credentials at all
    - ambiguous: cred_type -> [candidate list] when >1 match exists
    """
    resolved: dict[str, str] = dict(already_resolved)
    pending: list[str] = []
    ambiguous: dict[str, list[dict]] = {}

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
            if len(candidates) == 1:
                resolved[cred_type] = candidates[0]["id"]
                found = True
                break
            if len(candidates) > 1:
                ambiguous[cred_type] = candidates
                found = True
                break

        if not found:
            pending.append(cred_types[0])  # Request first option

    return resolved, pending, ambiguous
