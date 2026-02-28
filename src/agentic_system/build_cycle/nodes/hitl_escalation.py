"""Build Cycle HITL Escalation -- asks user when fix budget is exhausted."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState

log = logging.getLogger("aria.hitl")


class _Explanation(BaseModel):
    explanation: str


_explainer: BaseAgent[_Explanation] = BaseAgent(
    prompt=(
        "You are ARIA. An n8n workflow build failed and the auto-fix budget is exhausted. "
        "Write 2-3 sentences explaining what went wrong in plain English — no jargon, no markdown. "
        "Be specific: name the node, describe what the error means, and suggest the most likely cause. "
        "End with what the user should check or do before retrying."
    ),
    schema=_Explanation,
    name="HITLExplainer",
)


def _missing_node_explanation(error: dict) -> str:
    """Generate install instructions for a missing n8n node package."""
    node_name = error.get("node_name", "unknown node")
    message = error.get("message", "")

    return (
        f"The '{node_name}' step failed because it uses a node type that isn't installed "
        f"on your n8n instance. ARIA tried to substitute it with a built-in alternative "
        f"but couldn't find a suitable replacement.\n\n"
        f"To fix this, install the required package in your n8n instance:\n"
        f"  1. Open n8n Settings → Community Nodes\n"
        f"  2. Search for the package name shown in the error\n"
        f"  3. Click Install\n"
        f"  4. Come back here and choose 'Retry'\n\n"
        f"Alternatively, if you're running n8n via Docker, add the package to your Dockerfile:\n"
        f"  RUN npm install -g <package-name>\n\n"
        f"Error details: {message}"
    )


async def _generate_explanation(error: dict, fix_attempts: int) -> str:
    """Ask LLM to produce a plain-English explanation of the build failure."""
    error_type = error.get("type", "unknown")
    if error_type == "missing_node":
        return _missing_node_explanation(error)

    node_name = error.get("node_name", "unknown node")
    message = error.get("message", "no error message")
    prompt = (
        f"Node: {node_name}\n"
        f"Error type: {error_type}\n"
        f"Error message: {message}\n"
        f"Fix attempts made: {fix_attempts}\n"
        f"Description: {error.get('description') or 'none'}"
    )
    try:
        result: _Explanation = await _explainer.invoke([HumanMessage(content=prompt)])
        return result.explanation
    except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
        log.warning("HITLExplainer failed, using fallback: %s", exc)
        return (
            f"The '{node_name}' node failed after {fix_attempts} fix attempt(s). "
            f"Error: {message}"
        )


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

    explanation = await _generate_explanation(error, fix_attempts)

    user_decision: dict = interrupt({
        "type": "fix_exhausted",
        "paused_for_input": True,
        "explanation": explanation,
        "error": error,
        "fix_attempts": fix_attempts,
        "workflow_id": workflow_id,
        "n8n_url": n8n_url,
        "options": ["retry", "replan", "abort"],
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
        "nodes_to_build": [],
        "planned_edges": [],
        "node_build_results": [],
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
