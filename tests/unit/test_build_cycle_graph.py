"""Tests for the build cycle graph routing functions."""
import pytest
from src.agentic_system.build_cycle.nodes.modules._routers import (
    route_test_result,
    route_debugger_result,
    route_deploy_result,
)


def test_route_test_success():
    state = {"execution_result": {"status": "success"}}
    assert route_test_result(state) == "activate"


def test_route_test_failure():
    state = {"execution_result": {"status": "error"}}
    assert route_test_result(state) == "debugger"


def test_route_debugger_schema_with_budget():
    state = {
        "classified_error": {"type": "schema"},
        "fix_attempts": 1,
        "workflow_json": {"nodes": []},
    }
    assert route_debugger_result(state) == "deploy"


def test_route_debugger_logic_with_budget():
    state = {
        "classified_error": {"type": "logic"},
        "fix_attempts": 1,
        "workflow_json": {"nodes": []},
    }
    assert route_debugger_result(state) == "deploy"


def test_route_debugger_missing_node_with_budget():
    state = {
        "classified_error": {"type": "missing_node"},
        "fix_attempts": 1,
        "workflow_json": {"nodes": []},
    }
    assert route_debugger_result(state) == "deploy"


def test_route_debugger_auth_with_budget():
    state = {
        "classified_error": {"type": "auth"},
        "fix_attempts": 1,
        "workflow_json": {"nodes": []},
    }
    assert route_debugger_result(state) == "deploy"


def test_route_debugger_rate_limit():
    state = {"classified_error": {"type": "rate_limit"}, "fix_attempts": 0}
    assert route_debugger_result(state) == "test"


def test_route_debugger_no_budget():
    state = {
        "classified_error": {"type": "schema"},
        "fix_attempts": 3,
        "workflow_json": {"nodes": []},
    }
    assert route_debugger_result(state) == "hitl_fix_escalation"


def test_route_debugger_no_error():
    state = {}
    assert route_debugger_result(state) == "hitl_fix_escalation"


def test_route_deploy_success():
    state = {"status": "testing"}
    assert route_deploy_result(state) == "test"


def test_route_deploy_failure():
    state = {"status": "fixing"}
    assert route_deploy_result(state) == "debugger"
