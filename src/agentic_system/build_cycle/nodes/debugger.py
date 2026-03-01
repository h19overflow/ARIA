"""Build Cycle Debugger — two-phase: DiagnosticResearcher (RAG) + FixComposer (structured output).

Supports full-spectrum fixes: parameter patches, node type changes,
node additions/removals, and connection rewiring.
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from langchain_core.messages import AIMessage, HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, ClassifiedError
from src.agentic_system.build_cycle.schemas.execution import DebuggerOutput
from src.agentic_system.build_cycle.prompts.diagnostic_researcher import (
    DIAGNOSTIC_RESEARCHER_SYSTEM_PROMPT,
)
from src.agentic_system.build_cycle.prompts.debugger import FIX_COMPOSER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.nodes._credential_resolver import (
    extract_short_key,
    find_matching_credential,
)
from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP
from src.agentic_system.build_cycle.tools import search_n8n_nodes
from src.services.pipeline.event_bus import get_event_bus

log = logging.getLogger(__name__)

_FIXABLE_TYPES = {"schema", "logic", "missing_node"}

# Phase 1: Tool-use agent — searches ChromaDB for correct node schemas
_diagnostic_researcher = BaseAgent(
    prompt=DIAGNOSTIC_RESEARCHER_SYSTEM_PROMPT,
    schema=None,
    name="DiagnosticResearcher",
    tools=[search_n8n_nodes],
    recursion_limit=30,
)

# Phase 2: Structured output agent — produces the fix
_fix_composer = BaseAgent[DebuggerOutput](
    prompt=FIX_COMPOSER_SYSTEM_PROMPT,
    schema=DebuggerOutput,
    name="FixComposer",
    tools=[],
    recursion_limit=5,
)


async def debugger_node(state: ARIAState) -> dict:
    """Classify execution error and apply full-spectrum fix."""
    bus = get_event_bus(state)
    exec_result = state["execution_result"]
    workflow_json = state["workflow_json"]
    fix_attempts = state.get("fix_attempts", 0)
    error_data = exec_result.get("error") or {}
    cred_ids = state.get("resolved_credential_ids", {})

    if bus:
        await bus.emit_start(
            "fix", "Debugger",
            f"Fix attempt {fix_attempts + 1}/3 for {error_data.get('node_name', 'unknown')}",
        )
    start = time.monotonic()

    # ── Fast path: auth auto-attach (no LLM needed) ──────────────────
    error_msg = error_data.get("message", "")
    if _looks_like_auth_error(error_msg):
        patched = _try_attach_credentials(
            workflow_json, error_data.get("node_name", ""), cred_ids,
        )
        if patched:
            return await _auth_auto_attach_result(
                bus, start, fix_attempts, error_data, patched,
            )

    # ── Two-phase LLM fix ─────────────────────────────────────────────
    available_packages = state.get("available_node_packages", ["n8n-nodes-base"])
    compact_workflow = _summarize_workflow(workflow_json, error_data.get("node_name"))

    # Phase 1: Researcher diagnoses the issue
    diagnostic_report = await _run_diagnostic_researcher(
        error_data, compact_workflow, available_packages,
    )

    # Phase 2: Composer produces the structured fix
    result = await _run_fix_composer(
        diagnostic_report, error_data, compact_workflow,
        fix_attempts, available_packages,
    )

    classified: ClassifiedError = {
        "type": result.error_type,
        "node_name": result.node_name,
        "message": result.message,
        "description": result.description,
        "line_number": None,
        "stack": error_data.get("stack"),
    }

    has_fix = _has_any_fix(result)
    updates: dict = {
        "classified_error": classified,
        "fix_attempts": fix_attempts + 1,
        "messages": [HumanMessage(
            content=f"[Debugger] {result.error_type} in '{result.node_name}': {result.message}"
        )],
    }

    if has_fix:
        updates["workflow_json"] = _apply_full_fix(workflow_json, result)
        updates["status"] = "building"
        updates["messages"].append(HumanMessage(
            content=f"[Debugger] Fix applied — {_describe_fix(result)}"
        ))

    elapsed = int((time.monotonic() - start) * 1000)
    fix_status = "success" if has_fix else "error"
    if bus:
        await bus.emit_complete(
            "fix", "Debugger", fix_status,
            f"Debugger {result.error_type}: {result.message}", duration_ms=elapsed,
        )

    return updates


# ── Phase 1: Diagnostic Researcher ───────────────────────────────────────────

async def _run_diagnostic_researcher(
    error_data: dict,
    compact_workflow: dict,
    available_packages: list[str],
) -> str:
    """Run the Researcher to produce a diagnostic report via RAG search."""
    prompt = (
        f"## Error\n{json.dumps(error_data, indent=2)}\n\n"
        f"## Workflow\n{json.dumps(compact_workflow, indent=2)}\n\n"
        f"## Available packages\n{json.dumps(available_packages, indent=2)}"
    )
    result: AIMessage = await _diagnostic_researcher.invoke(
        [HumanMessage(content=prompt)]
    )
    log.info("[DiagnosticResearcher] Report produced (%d chars)", len(result.content))
    return result.content


# ── Phase 2: Fix Composer ─────────────────────────────────────────────────────

async def _run_fix_composer(
    diagnostic_report: str,
    error_data: dict,
    compact_workflow: dict,
    fix_attempts: int,
    available_packages: list[str],
) -> DebuggerOutput:
    """Run the Composer to produce a structured fix."""
    prompt = (
        f"Attempt: {fix_attempts + 1}/3\n\n"
        f"## Diagnostic Report\n{diagnostic_report}\n\n"
        f"## Error\n{json.dumps(error_data, indent=2)}\n\n"
        f"## Workflow\n{json.dumps(compact_workflow, indent=2)}\n\n"
        f"## Available packages\n{json.dumps(available_packages, indent=2)}"
    )
    return await _fix_composer.invoke([HumanMessage(content=prompt)])


# ── Full-spectrum fix application ─────────────────────────────────────────────

def _apply_full_fix(workflow_json: dict, result: DebuggerOutput) -> dict:
    """Apply all fix operations to the workflow JSON."""
    patched = dict(workflow_json)
    nodes = list(patched.get("nodes", []))

    # 1. Remove nodes
    if result.removed_node_names:
        removed = set(result.removed_node_names)
        nodes = [n for n in nodes if n.get("name") not in removed]

    # 2. Patch existing nodes (parameters, type, credentials)
    if result.fixed_nodes:
        for fix in result.fixed_nodes:
            for i, node in enumerate(nodes):
                if node.get("name") == fix.node_name:
                    nodes[i] = _patch_node(node, fix)
                    break

    # 3. Add new nodes
    if result.added_nodes:
        for new_node in result.added_nodes:
            nodes.append({
                "id": str(uuid.uuid4()),
                "name": new_node.name,
                "type": new_node.type,
                "typeVersion": 1,
                "position": new_node.position,
                "parameters": new_node.parameters,
                **({"credentials": new_node.credentials} if new_node.credentials else {}),
            })

    patched["nodes"] = nodes

    # 4. Replace connections if provided
    if result.fixed_connections is not None:
        patched["connections"] = result.fixed_connections

    return patched


def _patch_node(node: dict, fix) -> dict:
    """Apply a FixedNode patch to an existing node dict."""
    patched = dict(node)
    patched["parameters"] = fix.parameters
    if fix.new_type:
        patched["type"] = fix.new_type
    if fix.credentials:
        patched["credentials"] = fix.credentials
    return patched


# ── Auth auto-attach (fast path, no LLM) ─────────────────────────────────────

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
    bus, start: float, fix_attempts: int, error_data: dict, patched: dict,
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_any_fix(result: DebuggerOutput) -> bool:
    """Check if the DebuggerOutput contains any fix operations."""
    return any([
        result.fixed_nodes,
        result.fixed_connections is not None,
        result.added_nodes,
        result.removed_node_names,
    ])


def _describe_fix(result: DebuggerOutput) -> str:
    """Human-readable summary of what the fix changed."""
    parts = []
    if result.fixed_nodes:
        parts.append(f"patched {len(result.fixed_nodes)} node(s)")
    if result.added_nodes:
        parts.append(f"added {len(result.added_nodes)} node(s)")
    if result.removed_node_names:
        parts.append(f"removed {len(result.removed_node_names)} node(s)")
    if result.fixed_connections is not None:
        parts.append("rewired connections")
    return ", ".join(parts) if parts else "no changes"


def _summarize_workflow(workflow_json: dict, failing_node_name: str | None) -> dict:
    """Compact workflow for the debugger prompt.

    The failing node keeps full parameters (the LLM needs them to produce a fix).
    All other nodes are summarised to name/type/credentials only.
    """
    summary = {k: v for k, v in workflow_json.items() if k != "nodes"}
    compact_nodes = []
    for node in workflow_json.get("nodes", []):
        if node.get("name") == failing_node_name:
            compact_nodes.append(node)
        else:
            short: dict = {
                "name": node.get("name"),
                "type": node.get("type"),
            }
            if node.get("credentials"):
                short["credentials"] = node["credentials"]
            compact_nodes.append(short)
    summary["nodes"] = compact_nodes
    return summary
