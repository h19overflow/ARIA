"""Build Cycle Debugger — classify error AND apply fix in a single LLM call.

Replaces the sequential error_classifier_node → fix_node pair, halving
LLM call count and latency on the critical recovery path.
"""
from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, ClassifiedError
from src.agentic_system.build_cycle.schemas.execution import DebuggerOutput
from src.agentic_system.build_cycle.prompts.debugger import DEBUGGER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.nodes._credential_resolver import (
    _extract_short_key,
    _find_matching_credential,
)
from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP
from src.services.pipeline.event_bus import get_event_bus


_agent = BaseAgent[DebuggerOutput](
    prompt=DEBUGGER_SYSTEM_PROMPT,
    schema=DebuggerOutput,
    name="Debugger",
)

_FIXABLE_TYPES = {"schema", "logic"}


async def debugger_node(state: ARIAState) -> dict:
    """Classify execution error and apply fix in one LLM call."""
    bus = get_event_bus(state)
    exec_result = state["execution_result"]
    workflow_json = state["workflow_json"]
    fix_attempts = state.get("fix_attempts", 0)
    error_data = exec_result.get("error") or {}

    if bus:
        await bus.emit_start(
            "fix", "Debugger",
            f"Fix attempt {fix_attempts + 1}/3 for {error_data.get('node_name', 'unknown')}",
        )
    start = time.monotonic()

    prompt = (
        f"Attempt: {fix_attempts + 1}/3\n"
        f"Error:\n{json.dumps(error_data, indent=2)}\n\n"
        f"Workflow:\n{json.dumps(workflow_json, indent=2)}"
    )
    result: DebuggerOutput = await _agent.invoke([HumanMessage(content=prompt)])

    classified: ClassifiedError = {
        "type": result.error_type,
        "node_name": result.node_name,
        "message": result.message,
        "description": result.description,
        "line_number": result.line_number,
        "stack": error_data.get("stack"),
    }

    # ── Auth error auto-attach ───────────────────────────────────────
    if result.error_type == "auth":
        cred_ids = state.get("resolved_credential_ids", {})
        patched = await _try_attach_credentials(workflow_json, result.node_name, cred_ids)
        if patched:
            if bus:
                await bus.emit_warning(
                    "fix", result.node_name,
                    f"Auto-attached credentials for '{result.node_name}'",
                )
            elapsed = int((time.monotonic() - start) * 1000)
            if bus:
                await bus.emit_complete(
                    "fix", "Debugger", "success",
                    f"Auto-attached credentials for '{result.node_name}'",
                    duration_ms=elapsed,
                )
            return {
                "classified_error": classified,
                "fix_attempts": fix_attempts + 1,
                "workflow_json": patched,
                "status": "building",
                "messages": [HumanMessage(
                    content=f"[Debugger] Auto-attached credentials for '{result.node_name}' — retrying deploy"
                )],
            }

    updates: dict = {
        "classified_error": classified,
        "fix_attempts": fix_attempts + 1,
        "messages": [HumanMessage(
            content=f"[Debugger] {result.error_type} in '{result.node_name}': {result.message}"
        )],
    }

    if result.error_type in _FIXABLE_TYPES and result.fixed_parameters is not None:
        updates["workflow_json"] = _apply_fix(workflow_json, result)
        updates["status"] = "building"
        updates["messages"].append(HumanMessage(
            content=f"[Debugger] Fix applied to '{result.node_name}': {result.explanation}"
        ))

    elapsed = int((time.monotonic() - start) * 1000)
    fix_status = "success" if updates.get("status") == "building" else "error"
    if bus:
        await bus.emit_complete(
            "fix", "Debugger", fix_status,
            f"Debugger {result.error_type}: {result.message}", duration_ms=elapsed,
        )

    return updates


def _apply_fix(workflow_json: dict, result: DebuggerOutput) -> dict:
    """Patch the target node's parameters in place."""
    patched = dict(workflow_json)
    nodes = list(patched.get("nodes", []))
    for i, node in enumerate(nodes):
        if node["name"] == result.node_name:
            nodes[i] = {**node, "parameters": result.fixed_parameters}
            break
    patched["nodes"] = nodes
    return patched


log = logging.getLogger(__name__)


async def _try_attach_credentials(
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
            return None  # already has credentials — not a missing-cred issue

        short_key = _extract_short_key(node.get("type", ""))
        cred_types = NODE_CREDENTIAL_MAP.get(short_key, [])
        matched = _find_matching_credential(cred_types, resolved_credential_ids)
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
