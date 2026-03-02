"""Debugger — auth auto-attach fast path (no LLM needed)."""
from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ClassifiedError
from src.agentic_system.build_cycle.nodes.modules._credential_resolver import (
    extract_short_key,
    find_matching_credential,
)
from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP

log = logging.getLogger(__name__)


def _looks_like_auth_error(error_msg: str) -> bool:
    """Quick heuristic check for auth-related error messages."""
    auth_signals = ("401", "403", "unauthorized", "invalid credentials", "token expired")
    lower = error_msg.lower()
    return any(signal in lower for signal in auth_signals)


def _try_attach_credentials(
    workflow_json: dict,
    node_name: str,
    resolved_credential_ids: dict[str, str],
) -> dict | None:
    """Try to attach credentials to a node missing them. Returns patched workflow or None."""
    nodes = workflow_json.get("nodes", [])
    for i, node in enumerate(nodes):
        if node.get("name") != node_name:
            continue
        if node.get("credentials"):
            return None

        short_key = extract_short_key(node.get("type", ""))
        cred_types = NODE_CREDENTIAL_MAP.get(short_key, [])
        matched = find_matching_credential(cred_types, resolved_credential_ids)
        if not matched:
            return None

        cred_type, cred_id = matched
        patched = dict(workflow_json)
        patched_nodes = list(nodes)
        patched_nodes[i] = {
            **node,
            "credentials": {cred_type: {"id": cred_id, "name": cred_type}},
        }
        patched["nodes"] = patched_nodes
        log.info("Auto-attached credential %s (id=%s) to node '%s'", cred_type, cred_id, node_name)
        return patched
    return None


async def _auth_auto_attach_result(
    bus, start: float, fix_attempts: int, error_data: dict[str, Any], patched: dict,
) -> dict:
    """Build result dict for the auth auto-attach fast path."""
    node_name = error_data.get("node_name", "unknown")
    if bus:
        await bus.emit_warning("fix", node_name, f"Auto-attached credentials for '{node_name}'")
    elapsed = int((time.monotonic() - start) * 1000)
    if bus:
        await bus.emit_complete(
            "fix", "Debugger", "success",
            f"Auto-attached credentials for '{node_name}'", duration_ms=elapsed,
        )
    classified: ClassifiedError = {
        "type": "auth",
        "node_name": node_name,
        "message": error_data.get("message", ""),
        "description": error_data.get("description"),
        "line_number": None,
        "stack": error_data.get("stack"),
    }
    return {
        "classified_error": classified,
        "fix_attempts": fix_attempts + 1,
        "workflow_json": patched,
        "status": "building",
        "messages": [HumanMessage(
            content=f"[Debugger] Auto-attached credentials for '{node_name}' — retrying deploy"
        )],
    }
