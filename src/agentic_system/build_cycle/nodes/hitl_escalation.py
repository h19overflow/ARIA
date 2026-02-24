"""Build Cycle HITL Escalation -- asks user when fix budget is exhausted."""
from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.agentic_system.shared.state import ARIAState


async def hitl_fix_escalation_node(state: ARIAState) -> dict:
    """Escalate to user when fix budget is exhausted or error is unfixable.

    Unified resume schema:
      {"action": "retry"}   — user fixed the node manually in the n8n UI and wants ARIA to retest
      {"action": "replan"}  — start over through preflight
      {"action": "abort"}   — give up
    """
    error = state.get("classified_error") or {}
    fix_attempts = state.get("fix_attempts", 0)
    workflow_id = state.get("n8n_workflow_id")

    n8n_url = f"http://localhost:5678/workflow/{workflow_id}" if workflow_id else "the n8n UI"

    user_decision: dict = interrupt({
        "type": "fix_exhausted",
        "paused_for_input": True,
        "error": error,
        "fix_attempts": fix_attempts,
        "workflow_id": workflow_id,
        "options": ["retry", "replan", "abort"],
        "instructions": (
            f"ARIA could not auto-fix the error after {fix_attempts} attempt(s). "
            f"Please open {n8n_url}, fix the '{error.get('node_name', 'unknown')}' node manually, "
            f"then choose 'retry' to let ARIA retest, 'replan' to start over, or 'abort' to cancel."
        ),
    })

    return _handle_user_decision(user_decision, state)


def _handle_user_decision(decision: dict | str, state: ARIAState) -> dict:
    """Route user's HITL decision to appropriate state update."""
    if isinstance(decision, str):
        action = decision
    else:
        action = decision.get("action", "abort")

    if action == "retry":
        return _reset_for_retry(state)
    if action == "replan":
        return _reset_for_replan(state)
    return _abort(state)


def _reset_for_retry(state: ARIAState) -> dict:
    """User fixed the workflow in n8n — reset fix budget and retest."""
    return {
        "fix_attempts": 0,
        "classified_error": None,
        "execution_result": None,
        "paused_for_input": False,
        "status": "testing",
        "messages": [HumanMessage(
            content="[HITL] Retesting after manual fix in n8n UI.",
        )],
    }


def _reset_for_replan(state: ARIAState) -> dict:
    """Reset build state for a full replan through preflight."""
    return {
        "workflow_json": None,
        "n8n_workflow_id": None,
        "fix_attempts": 0,
        "classified_error": None,
        "execution_result": None,
        "node_templates": [],
        "build_phase": 0,
        "total_phases": 0,
        "phase_node_map": [],
        "paused_for_input": False,
        "status": "replanning",
        "messages": [HumanMessage(
            content="[HITL] Replanning -- returning to orchestrator.",
        )],
    }


def _abort(state: ARIAState) -> dict:
    """Mark pipeline as failed."""
    return {
        "paused_for_input": False,
        "status": "failed",
        "messages": [HumanMessage(content="[HITL] User chose to abort.")],
    }
