"""Conditional-edge routers for the Build Cycle graph."""
from __future__ import annotations

from src.agentic_system.shared.state import ARIAState

MAX_FIX_ATTEMPTS = 3
_FIXABLE_TYPES = {"schema", "logic", "missing_node", "auth"}


def route_test_result(state: ARIAState) -> str:
    """Route based on execution result: activate on success or debug on failure."""
    result = state.get("execution_result")
    if result and result["status"] == "success":
        return "activate"
    return "debugger"


def route_debugger_result(state: ARIAState) -> str:
    """Route after Debugger: re-deploy if fix was applied, else escalate."""
    error = state.get("classified_error")
    if not error:
        return "hitl_fix_escalation"

    error_type = error.get("type")
    has_budget = state.get("fix_attempts", 0) < MAX_FIX_ATTEMPTS

    if error_type == "rate_limit":
        return "test"
    if error_type in _FIXABLE_TYPES and has_budget and state.get("workflow_json"):
        return "deploy"
    return "hitl_fix_escalation"


def route_deploy_result(state: ARIAState) -> str:
    """Route after deploy: test on success, debugger on failure."""
    if state.get("status") == "fixing":
        return "debugger"
    return "test"


def route_hitl_decision(state: ARIAState) -> str:
    """Route after HITL escalation based on user's chosen action."""
    status = state.get("status", "failed")
    if status == "building":
        return "deploy"
    if status == "testing":
        return "test"
    return "fail"
