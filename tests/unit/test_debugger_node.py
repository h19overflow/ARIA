"""Tests for the two-phase debugger orchestration."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from src.agentic_system.build_cycle.nodes.debugger import debugger_node
from src.agentic_system.build_cycle.nodes.modules._debugger_fix import _apply_full_fix
from src.agentic_system.build_cycle.schemas.execution import DebuggerOutput, FixedNode


@pytest.fixture
def base_state():
    return {
        "execution_result": {
            "status": "error",
            "error": {
                "node_name": "Gmail",
                "message": "Missing field 'to'",
                "description": None,
                "line_number": None,
                "stack": None,
            },
        },
        "workflow_json": {
            "name": "Test Workflow",
            "nodes": [
                {"id": "1", "name": "Trigger", "type": "n8n-nodes-base.webhook",
                 "parameters": {"path": "test"}, "position": [100, 200]},
                {"id": "2", "name": "Gmail", "type": "n8n-nodes-base.gmail",
                 "parameters": {}, "position": [300, 200]},
            ],
            "connections": {
                "Trigger": {"main": [[{"node": "Gmail", "type": "main", "index": 0}]]},
            },
        },
        "fix_attempts": 0,
        "resolved_credential_ids": {},
    }


def test_apply_full_fix_patches_node_parameters():
    workflow = {
        "nodes": [
            {"name": "Gmail", "type": "n8n-nodes-base.gmail", "parameters": {}},
        ],
        "connections": {},
    }
    output = {
        "error_type": "schema",
        "node_name": "Gmail",
        "message": "fix",
        "fixed_nodes": [{"node_name": "Gmail", "parameters": {"to": "a@b.com"}}],
    }
    result = _apply_full_fix(workflow, output)
    assert result["nodes"][0]["parameters"] == {"to": "a@b.com"}


def test_apply_full_fix_changes_node_type():
    workflow = {
        "nodes": [
            {"name": "AI Agent", "type": "n8n-nodes-langchain.agent",
             "parameters": {"model": "gpt-4"}, "position": [200, 200]},
        ],
        "connections": {},
    }
    output = {
        "error_type": "missing_node",
        "node_name": "AI Agent",
        "message": "Node type not installed",
        "fixed_nodes": [{
            "node_name": "AI Agent",
            "parameters": {"url": "https://api.openai.com/v1/chat"},
            "new_type": "n8n-nodes-base.httpRequest",
        }],
    }
    result = _apply_full_fix(workflow, output)
    assert result["nodes"][0]["type"] == "n8n-nodes-base.httpRequest"
    assert result["nodes"][0]["parameters"]["url"] == "https://api.openai.com/v1/chat"
    assert result["nodes"][0]["name"] == "AI Agent"


def test_apply_full_fix_adds_and_removes_nodes():
    workflow = {
        "nodes": [
            {"name": "Trigger", "type": "n8n-nodes-base.webhook", "parameters": {},
             "position": [100, 200]},
            {"name": "Old Node", "type": "n8n-nodes-base.code", "parameters": {},
             "position": [300, 200]},
        ],
        "connections": {"Trigger": {"main": [[{"node": "Old Node", "type": "main", "index": 0}]]}},
    }
    output = {
        "error_type": "logic",
        "node_name": "Old Node",
        "message": "Replace with better approach",
        "removed_node_names": ["Old Node"],
        "added_nodes": [{
            "name": "New Transform",
            "type": "n8n-nodes-base.code",
            "parameters": {"jsCode": "return items;"},
            "position": [300, 200],
        }],
        "fixed_connections": {"Trigger": {"main": [[{"node": "New Transform", "type": "main", "index": 0}]]}},
    }
    result = _apply_full_fix(workflow, output)
    node_names = [n["name"] for n in result["nodes"]]
    assert "Old Node" not in node_names
    assert "New Transform" in node_names
    assert result["connections"]["Trigger"]["main"][0][0]["node"] == "New Transform"


def test_apply_full_fix_rewires_connections():
    workflow = {
        "nodes": [
            {"name": "A", "type": "n8n-nodes-base.webhook", "parameters": {}},
            {"name": "B", "type": "n8n-nodes-base.code", "parameters": {}},
        ],
        "connections": {"A": {"main": [[{"node": "B", "type": "main", "index": 0}]]}},
    }
    new_connections = {"A": {"main": [[{"node": "B", "type": "main", "index": 0}, {"node": "B", "type": "main", "index": 1}]]}}
    output = {
        "error_type": "schema",
        "node_name": "B",
        "message": "fix connections",
        "fixed_connections": new_connections,
    }
    result = _apply_full_fix(workflow, output)
    assert result["connections"] == new_connections


def test_apply_full_fix_attaches_credentials():
    workflow = {
        "nodes": [
            {"name": "Gmail", "type": "n8n-nodes-base.gmail", "parameters": {}},
        ],
        "connections": {},
    }
    output = {
        "error_type": "schema",
        "node_name": "Gmail",
        "message": "fix",
        "fixed_nodes": [{
            "node_name": "Gmail",
            "parameters": {"to": "a@b.com"},
            "credentials": {"gmailOAuth2Api": {"id": "cred-123", "name": "gmailOAuth2Api"}},
        }],
    }
    result = _apply_full_fix(workflow, output)
    assert result["nodes"][0]["credentials"]["gmailOAuth2Api"]["id"] == "cred-123"


@pytest.mark.asyncio
async def test_debugger_node_calls_researcher_then_composer(base_state):
    fake_report = AIMessage(content="## Root Cause\nMissing 'to' field on Gmail node")
    fake_output = DebuggerOutput(
        error_type="schema",
        node_name="Gmail",
        message="Missing 'to' field",
        fixed_nodes=[FixedNode(node_name="Gmail", parameters={"to": "a@b.com"})],
    )

    with patch(
        "src.agentic_system.build_cycle.nodes.debugger._diagnostic_researcher"
    ) as mock_researcher, patch(
        "src.agentic_system.build_cycle.nodes.debugger._fix_composer"
    ) as mock_composer:
        mock_researcher.invoke = AsyncMock(return_value=fake_report)
        mock_composer.invoke = AsyncMock(return_value=fake_output)

        result = await debugger_node(base_state)

        mock_researcher.invoke.assert_awaited_once()
        mock_composer.invoke.assert_awaited_once()
        assert result["classified_error"]["type"] == "schema"
        assert result["workflow_json"]["nodes"][1]["parameters"] == {"to": "a@b.com"}
        assert result["status"] == "building"


@pytest.mark.asyncio
async def test_debugger_node_composer_returns_none_does_not_crash(base_state):
    """When FixComposer.invoke() returns None (Gemini structured output failure),
    the node must NOT crash with AttributeError and should return a stable state update."""
    fake_report = AIMessage(content="## Root Cause\nsome diagnostic")

    with patch(
        "src.agentic_system.build_cycle.nodes.debugger._diagnostic_researcher"
    ) as mock_researcher, patch(
        "src.agentic_system.build_cycle.nodes.debugger._fix_composer"
    ) as mock_composer:
        mock_researcher.invoke = AsyncMock(return_value=fake_report)
        # Simulate base_agent returning None (structured_response key missing)
        mock_composer.invoke = AsyncMock(return_value=None)

        result = await debugger_node(base_state)

        # Should not crash; should return a valid update dict
        assert isinstance(result, dict)
        assert "classified_error" in result
        assert result["classified_error"]["type"] == "unknown"
        assert result["fix_attempts"] == 1


@pytest.mark.asyncio
async def test_debugger_node_auth_auto_attach_shortcut(base_state):
    """Auth errors with matching credentials skip LLM entirely."""
    base_state["execution_result"]["error"]["message"] = "401 Unauthorized"
    base_state["resolved_credential_ids"] = {"gmailOAuth2Api": "cred-123"}

    with patch(
        "src.agentic_system.build_cycle.nodes.debugger._try_attach_credentials",
        return_value={
            "name": "Test Workflow",
            "nodes": [
                {"id": "1", "name": "Trigger", "type": "n8n-nodes-base.webhook",
                 "parameters": {"path": "test"}, "position": [100, 200]},
                {"id": "2", "name": "Gmail", "type": "n8n-nodes-base.gmail",
                 "parameters": {},
                 "credentials": {"gmailOAuth2Api": {"id": "cred-123", "name": "gmailOAuth2Api"}},
                 "position": [300, 200]},
            ],
            "connections": {},
        },
    ), patch(
        "src.agentic_system.build_cycle.nodes.debugger._diagnostic_researcher"
    ) as mock_researcher, patch(
        "src.agentic_system.build_cycle.nodes.debugger._fix_composer"
    ) as mock_composer:
        mock_researcher.invoke = AsyncMock(
            return_value=AIMessage(content="## Root Cause\nAuth error")
        )
        mock_composer.invoke = AsyncMock(
            return_value=DebuggerOutput(
                error_type="auth", node_name="Gmail", message="401"
            )
        )

        result = await debugger_node(base_state)

        # Auth auto-attach fast path skips LLM entirely
        mock_researcher.invoke.assert_not_awaited()
        mock_composer.invoke.assert_not_awaited()
        assert result["fix_attempts"] == 1
        assert result["status"] == "building"
