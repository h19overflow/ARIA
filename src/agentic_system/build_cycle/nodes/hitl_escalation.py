"""Build Cycle HITL Escalation -- asks user when fix budget is exhausted."""
from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.agentic_system.shared.state import ARIAState


async def hitl_fix_escalation_node(state: ARIAState) -> dict:
    """Escalate to user when fix budget is exhausted or error is unfixable."""
    error = state.get("classified_error", {})
    fix_attempts = state.get("fix_attempts", 0)

    user_decision: dict = interrupt({
        "type": "fix_exhausted",
        "error": error,
        "fix_attempts": fix_attempts,
        "workflow_id": state.get("n8n_workflow_id"),
        "options": ["manual_fix", "replan", "abort"],
        "message": (
            f"Fix budget exhausted after {fix_attempts} attempts. "
            f"Error in '{error.get('node_name', 'unknown')}': "
            f"{error.get('message', 'unknown')}. "
            f"Choose: manual_fix, replan, or abort."
        ),
    })

    return _handle_user_decision(user_decision, state)


def _handle_user_decision(decision: dict, state: ARIAState) -> dict:
    """Route user's HITL decision to appropriate state update."""
    action = decision.get("action", "abort")

    if action == "manual_fix":
        return _apply_manual_fix(decision, state)
    if action == "replan":
        return _reset_for_replan(state)
    return _abort(state)


def _apply_manual_fix(decision: dict, state: ARIAState) -> dict:
    """Apply user-provided patch to workflow and reset fix budget."""
    workflow = dict(state.get("workflow_json") or {})
    patch = decision.get("patch", {})
    node_name = patch.get("node_name")
    new_params = patch.get("parameters")

    if node_name and new_params:
        nodes = list(workflow.get("nodes", []))
        for i, node in enumerate(nodes):
            if node["name"] == node_name:
                nodes[i] = {**node, "parameters": new_params}
                break
        workflow["nodes"] = nodes

    return {
        "workflow_json": workflow,
        "fix_attempts": 0,
        "classified_error": None,
        "execution_result": None,
        "status": "building",
        "messages": [HumanMessage(
            content=f"[HITL] Manual fix applied to '{node_name}'.",
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
        "status": "replanning",
        "messages": [HumanMessage(
            content="[HITL] Replanning -- returning to orchestrator.",
        )],
    }


def _abort(state: ARIAState) -> dict:
    """Mark pipeline as failed."""
    return {
        "status": "failed",
        "messages": [HumanMessage(content="[HITL] User chose to abort.")],
    }
