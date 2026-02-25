"""Pre-Flight Credential Scanner -- deterministic (no LLM)."""
from __future__ import annotations

import logging

import httpx
from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.agentic_system.shared.credential_utils import (
    classify_node_credentials,
    fuzzy_match_credential_types,
    group_by_type,
)
from src.agentic_system.shared.node_credential_map import (
    NODE_CREDENTIAL_MAP,
    get_credential_types,
)
from src.agentic_system.shared.state import ARIAState
from src.boundary.n8n.client import N8nClient

logger = logging.getLogger(__name__)


async def credential_scanner_node(state: ARIAState) -> dict:
    """Scan required node types against saved n8n credentials.

    Deterministic replacement for the former LLM-based scanner agent.
    """
    required_nodes: list[str] = state["required_nodes"]
    already_resolved: dict[str, str] = dict(state.get("resolved_credential_ids", {}))
    logger.info("[CredentialScanner] Scanning %d node type(s)", len(required_nodes))

    resolved, pending, ambiguous = await _scan_credentials(required_nodes)
    resolved = {**already_resolved, **resolved}

    if ambiguous:
        resolved = _apply_hitl_choices(resolved, ambiguous)
        pending = [t for t in pending if t not in resolved]

    summary = f"{len(resolved)} resolved, {len(pending)} pending, {len(ambiguous)} ambiguous"
    status_msg = _build_status_message(pending, ambiguous, summary)
    logger.info("[CredentialScanner] %s", summary)

    return {
        "resolved_credential_ids": resolved,
        "pending_credential_types": pending,
        "paused_for_input": False,
        "messages": [HumanMessage(content=status_msg)],
    }


async def _scan_credentials(
    node_types: list[str],
) -> tuple[dict[str, str], list[str], dict[str, list[dict]]]:
    """Classify each node type's credentials against saved n8n creds."""
    client = N8nClient()
    await client.connect()
    try:
        saved = await client.list_credentials()
        saved_by_type = group_by_type(saved)
        resolved, pending, ambiguous = _classify_all_nodes(
            node_types, saved_by_type,
        )
        unknown = [n for n in node_types if n not in NODE_CREDENTIAL_MAP]
        if unknown:
            await _resolve_unknown_nodes(
                unknown, client, saved_by_type, resolved, pending, ambiguous,
            )
    except httpx.HTTPStatusError:
        logger.exception("[CredentialScanner] n8n API call failed")
        resolved, pending, ambiguous = {}, [], {}
    finally:
        await client.disconnect()
    return resolved, pending, ambiguous


def _classify_all_nodes(
    node_types: list[str],
    saved_by_type: dict[str, list[dict]],
) -> tuple[dict[str, str], list[str], dict[str, list[dict]]]:
    """Run classify for every node type found in NODE_CREDENTIAL_MAP."""
    resolved: dict[str, str] = {}
    pending: list[str] = []
    ambiguous: dict[str, list[dict]] = {}
    for node_type in node_types:
        cred_types = get_credential_types(node_type)
        if not cred_types or any(ct in resolved for ct in cred_types):
            continue
        classify_node_credentials(cred_types, saved_by_type, resolved, pending, ambiguous)
    return resolved, pending, ambiguous


async def _resolve_unknown_nodes(
    unknown_nodes: list[str],
    client: N8nClient,
    saved_by_type: dict[str, list[dict]],
    resolved: dict[str, str],
    pending: list[str],
    ambiguous: dict[str, list[dict]],
) -> None:
    """Fuzzy-match unknown node types against n8n's credential type registry."""
    all_types = await client.list_credential_types()
    for node_type in unknown_nodes:
        matched = fuzzy_match_credential_types(node_type, all_types)
        if not matched or any(ct in resolved for ct in matched):
            continue
        classify_node_credentials(matched, saved_by_type, resolved, pending, ambiguous)


def _apply_hitl_choices(
    resolved: dict[str, str],
    ambiguous: dict[str, list[dict]],
) -> dict[str, str]:
    """Interrupt to let the user pick one credential per ambiguous type."""
    response: dict = interrupt({
        "type": "credential_ambiguity",
        "paused_for_input": True,
        "ambiguous": {
            cred_type: [{"id": c["id"], "name": c.get("name", c["id"])} for c in candidates]
            for cred_type, candidates in ambiguous.items()
        },
        "message": "Multiple saved credentials found. Select one ID per type.",
    })
    selections: dict[str, str] = response.get("selections", {}) if isinstance(response, dict) else {}
    return {**resolved, **selections}


def _build_status_message(
    pending: list[str],
    ambiguous: dict[str, list[dict]],
    summary: str,
) -> str:
    """Build a human-readable status line for the scanner result."""
    if pending:
        return f"[Scanner] Missing credentials for: {', '.join(pending)}"
    if ambiguous:
        return f"[Scanner] Ambiguous credentials for: {', '.join(ambiguous)}"
    return f"[Scanner] All credentials resolved. {summary}"
