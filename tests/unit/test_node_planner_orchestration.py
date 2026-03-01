"""Tests for the two-phase node planner orchestration."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from langchain_core.messages import AIMessage, HumanMessage

from src.agentic_system.build_cycle.nodes.node_planner import (
    node_planner_node,
    _build_researcher_prompt,
    _build_composer_prompt,
)
from src.agentic_system.build_cycle.schemas.node_plan import NodePlan, NodeSpec, PlannedEdge


@pytest.fixture
def mock_state():
    return {
        "build_blueprint": {
            "topology": {"nodes": [], "edges": [], "entry_node": "", "branch_nodes": []},
            "intent": "Send a daily email summary",
        },
        "resolved_credential_ids": {"googleApi": "cred-123"},
    }


def _make_fake_plan() -> NodePlan:
    return NodePlan(
        workflow_name="Test Workflow",
        nodes=[
            NodeSpec(
                node_name="Schedule Trigger",
                node_type="n8n-nodes-base.scheduleTrigger",
                position_index=0,
            ),
            NodeSpec(
                node_name="Gmail",
                node_type="n8n-nodes-base.gmail",
                credential_type="googleApi",
                credential_id="cred-123",
                position_index=1,
            ),
        ],
        edges=[
            PlannedEdge(from_node="Schedule Trigger", to_node="Gmail"),
        ],
    )


def test_build_researcher_prompt_includes_intent():
    prompt = _build_researcher_prompt(
        intent="Send daily email",
        topology=None,
        cred_ids={"googleApi": "cred-123"},
        available_packages=["n8n-nodes-base"],
    )
    assert "Send daily email" in prompt
    assert "n8n-nodes-base" in prompt
    assert "googleApi" in prompt


def test_build_composer_prompt_includes_catalog():
    prompt = _build_composer_prompt(
        catalog="### Node 1: Gmail\n- type: n8n-nodes-base.gmail",
        intent="Send daily email",
        cred_ids={"googleApi": "cred-123"},
        available_packages=["n8n-nodes-base"],
    )
    assert "Node 1: Gmail" in prompt
    assert "Send daily email" in prompt


@pytest.mark.asyncio
async def test_node_planner_calls_researcher_then_composer(mock_state):
    fake_catalog = AIMessage(content="### Node 1: Schedule Trigger\n- type: n8n-nodes-base.scheduleTrigger")
    fake_plan = _make_fake_plan()

    with patch(
        "src.agentic_system.build_cycle.nodes.node_planner._researcher"
    ) as mock_researcher, patch(
        "src.agentic_system.build_cycle.nodes.node_planner._composer"
    ) as mock_composer, patch(
        "src.agentic_system.build_cycle.nodes.node_planner.discover_installed_node_prefixes",
        new_callable=AsyncMock,
        return_value={"n8n-nodes-base"},
    ):
        mock_researcher.invoke = AsyncMock(return_value=fake_catalog)
        mock_composer.invoke = AsyncMock(return_value=fake_plan)

        result = await node_planner_node(mock_state)

        mock_researcher.invoke.assert_awaited_once()
        mock_composer.invoke.assert_awaited_once()
        assert len(result["nodes_to_build"]) == 2
        assert result["planned_edges"][0]["from_node"] == "Schedule Trigger"


@pytest.mark.asyncio
async def test_node_planner_returns_empty_when_no_topology(mock_state):
    mock_state["build_blueprint"] = {}
    mock_state.pop("required_nodes", None)

    result = await node_planner_node(mock_state)

    assert result["nodes_to_build"] == []
    assert result["planned_edges"] == []
