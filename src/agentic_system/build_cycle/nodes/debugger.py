"""Build Cycle Debugger — two-phase: DiagnosticResearcher (RAG) + FixComposer (structured output)."""
from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.schemas.execution import DebuggerOutput
from src.agentic_system.build_cycle.prompts.diagnostic_researcher import (
    DIAGNOSTIC_RESEARCHER_SYSTEM_PROMPT,
)
from src.agentic_system.build_cycle.prompts.debugger import FIX_COMPOSER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.tools import search_n8n_nodes
from src.services.pipeline.event_bus import get_event_bus

from src.agentic_system.build_cycle.nodes._debugger_auth import (
    _looks_like_auth_error,
    _try_attach_credentials,
    _auth_auto_attach_result,
)
from src.agentic_system.build_cycle.nodes._debugger_fix import _build_fix_updates
from src.agentic_system.build_cycle.nodes._debugger_compact import _summarize_workflow

log = logging.getLogger(__name__)

_diagnostic_researcher = BaseAgent(
    prompt=DIAGNOSTIC_RESEARCHER_SYSTEM_PROMPT,
    schema=None,
    name="DiagnosticResearcher",
    tools=[search_n8n_nodes],
    recursion_limit=30,
)

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
    workflow_json = state.get("workflow_json") or {"nodes": [], "connections": {}}
    fix_attempts = state.get("fix_attempts", 0)
    error_data = exec_result.get("error") or {}

    if bus:
        await bus.emit_start(
            "fix", "Debugger",
            f"Fix attempt {fix_attempts + 1}/3 for {error_data.get('node_name', 'unknown')}",
        )
    start = time.monotonic()

    if _looks_like_auth_error(error_data.get("message", "")):
        cred_ids = state.get("resolved_credential_ids", {})
        patched = _try_attach_credentials(
            workflow_json, error_data.get("node_name", ""), cred_ids,
        )
        if patched:
            return await _auth_auto_attach_result(
                bus, start, fix_attempts, error_data, patched,
            )

    return await _run_two_phase_fix(state, error_data, workflow_json, fix_attempts, bus, start)


async def _run_two_phase_fix(
    state: ARIAState, error_data: dict, workflow_json: dict,
    fix_attempts: int, bus, start: float,
) -> dict:
    """Run DiagnosticResearcher → FixComposer and build state updates."""
    available_packages = state.get("available_node_packages", ["n8n-nodes-base"])
    compact_workflow = _summarize_workflow(workflow_json, error_data.get("node_name"))

    diagnostic_report = await _run_diagnostic_researcher(
        error_data, compact_workflow, available_packages,
    )
    result = await _run_fix_composer(
        diagnostic_report, error_data, compact_workflow,
        fix_attempts, available_packages,
    )

    updates = _build_fix_updates(workflow_json, result, error_data, fix_attempts)

    elapsed = int((time.monotonic() - start) * 1000)
    fix_status = "success" if updates.get("status") == "building" else "error"
    if bus:
        await bus.emit_complete(
            "fix", "Debugger", fix_status,
            f"Debugger {result.get('error_type', 'unknown')}: {result.get('message', '')}", duration_ms=elapsed,
        )
    return updates


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


_MAX_DIAGNOSTIC_CHARS = 8000
_MAX_PROMPT_CHARS = 30000


_FALLBACK_FIX_RESULT: dict = {
    "error_type": "unknown",
    "node_name": None,
    "message": "FixComposer returned no structured output",
    "description": None,
    "fixed_nodes": None,
    "fixed_connections": None,
    "added_nodes": None,
    "removed_node_names": None,
}


async def _run_fix_composer(
    diagnostic_report: str,
    error_data: dict,
    compact_workflow: dict,
    fix_attempts: int,
    available_packages: list[str],
) -> dict:
    """Run the Composer to produce a structured fix. Returns a plain dict.

    Guards against None output when the LLM fails to produce structured output
    (e.g. Gemini structured-output mode returns no ``structured_response`` key).
    """
    capped_report = _cap_text(diagnostic_report, _MAX_DIAGNOSTIC_CHARS)
    prompt = (
        f"Attempt: {fix_attempts + 1}/3\n\n"
        f"## Diagnostic Report\n{capped_report}\n\n"
        f"## Error\n{json.dumps(error_data, indent=2)}\n\n"
        f"## Workflow\n{json.dumps(compact_workflow, indent=2)}\n\n"
        f"## Available packages\n{json.dumps(available_packages, indent=2)}"
    )
    prompt = _cap_text(prompt, _MAX_PROMPT_CHARS)
    output = await _fix_composer.invoke([HumanMessage(content=prompt)])
    if output is None:
        log.warning("[FixComposer] Returned None (structured output failed); using fallback")
        return dict(_FALLBACK_FIX_RESULT)
    return output.model_dump()


def _cap_text(text: str, max_chars: int) -> str:
    """Truncate text with a marker if it exceeds max_chars."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [truncated]"
