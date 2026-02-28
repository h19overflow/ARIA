"""Build Cycle HITL Escalation -- asks user when fix budget is exhausted."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.schemas.execution import HITLExplanation

log = logging.getLogger("aria.hitl")





_explainer: BaseAgent[HITLExplanation] = BaseAgent(
    prompt=(
        "You are ARIA. An n8n workflow build failed and the auto-fix budget is exhausted. "
        "Write 2-3 sentences explaining what went wrong in plain English — no jargon, no markdown. "
        "Be specific: name the node, describe what the error means, and suggest the most likely cause. "
        "End with what the user should check or do before retrying."
    ),
    schema=HITLExplanation,
    name="HITLExplainer",
)


def _missing_node_explanation(error: dict) -> str:
    """Generate install instructions for a missing n8n node package."""
    node_name = error.get("node_name", "unknown node")
    message = error.get("message", "")
    description = error.get("description") or ""

    # Extract the node type from description if available (e.g. "Node type: @n8n/...")
    node_type = ""
    if "Node type:" in description:
        node_type = description.split("Node type:")[-1].strip()
    # Extract package name from the node type (e.g. "@n8n/n8n-nodes-langchain")
    package_name = node_type.rsplit(".", 1)[0] if "." in node_type else ""

    parts = [
        f"The '{node_name}' step failed because it uses a node type "
        f"({node_type or 'see error below'}) that isn't installed on your n8n instance.",
    ]

    if package_name:
        parts.append(
            f"ARIA tried to substitute it with a built-in alternative but couldn't.\n\n"
            f"To fix this, install the '{package_name}' package:\n"
            f"  1. Open n8n Settings > Community Nodes\n"
            f"  2. Search for '{package_name}'\n"
            f"  3. Click Install, then come back and choose 'Try Again'"
        )
    else:
        parts.append(
            "ARIA tried to substitute it with a built-in alternative but couldn't.\n\n"
            "To fix this:\n"
            "  1. Open n8n Settings > Community Nodes\n"
            "  2. Search for the package that provides this node type\n"
            "  3. Click Install, then come back and choose 'Try Again'"
        )

    if message:
        parts.append(f"Error: {message}")

    return "\n\n".join(parts)


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
        result: HITLExplanation = await _explainer.invoke([HumanMessage(content=prompt)])
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
      {"action": "discuss", "message": "..."} — user wants to ask a question about the error
    """
    error = state.get("classified_error") or {}
    fix_attempts = state.get("fix_attempts", 0)
    workflow_id = state.get("n8n_workflow_id")
    n8n_url = f"http://localhost:5678/workflow/{workflow_id}" if workflow_id else "the n8n UI"

    explanation = await _generate_explanation(error, fix_attempts)

    while True:
        user_decision = interrupt({
            "type": "fix_exhausted",
            "paused_for_input": True,
            "explanation": explanation,
            "error": error,
            "fix_attempts": fix_attempts,
            "workflow_id": workflow_id,
            "n8n_url": n8n_url,
            "options": ["retry", "replan", "discuss", "abort"],
        })

        action = (
            user_decision.get("action", "abort")
            if isinstance(user_decision, dict)
            else user_decision
        )

        if action != "discuss":
            break

        question = user_decision.get("message", "") if isinstance(user_decision, dict) else ""
        explanation = await _answer_user_question(question, error, state)

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


async def _answer_user_question(question: str, error: dict, state: ARIAState) -> str:
    """Use LLM to answer the user's question about the build failure."""
    workflow_id = state.get("n8n_workflow_id", "unknown")
    node_name = error.get("node_name", "unknown")
    error_msg = error.get("message", "")
    error_type = error.get("type", "unknown")
    description = error.get("description", "")

    prompt = (
        f"The user has a question about a failed n8n workflow build.\n\n"
        f"Error context:\n"
        f"  Node: {node_name}\n"
        f"  Error type: {error_type}\n"
        f"  Error message: {error_msg}\n"
        f"  Description: {description}\n"
        f"  Workflow ID: {workflow_id}\n\n"
        f"User's question: {question}\n\n"
        f"Answer clearly and specifically. If you don't know, say so."
    )
    try:
        result: HITLExplanation = await _explainer.invoke(
            [HumanMessage(content=prompt)]
        )
        return result.explanation
    except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
        log.warning("Discussion LLM failed: %s", exc)
        return f"Sorry, I couldn't process your question right now. Error: {exc}"


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
