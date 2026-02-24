"""Unit tests for orchestrator helpers: _handle_commit and _extract_topology."""
import pytest
from src.agentic_system.preflight.nodes.orchestrator import (
    _handle_commit,
    _extract_topology,
    _extract_blueprint_fields,
    _handle_clarify,
)
from src.agentic_system.preflight.schemas.blueprint import OrchestratorOutput
from src.agentic_system.preflight.schemas.orchestrator_decision import (
    OrchestratorDecision,
    ClarifyingQuestion,
)

pytestmark = pytest.mark.unit


def _make_output(**kwargs) -> OrchestratorOutput:
    defaults = dict(
        intent_summary="Send a Slack message via webhook",
        required_nodes=["webhook", "slack"],
        trigger_node="webhook",
        workflow_name="Webhook to Slack",
        topology={
            "nodes": ["Webhook", "Slack"],
            "edges": [{"from_node": "Webhook", "to_node": "Slack", "branch": None}],
            "entry_node": "Webhook",
            "branch_nodes": [],
        },
        user_description="Receive a webhook and post to Slack.",
    )
    defaults.update(kwargs)
    return OrchestratorOutput(**defaults)


def _make_output_no_topology(required_nodes: list, trigger_node: str) -> OrchestratorOutput:
    """Build OrchestratorOutput with topology set to None via model_construct (bypasses validation)."""
    return OrchestratorOutput.model_construct(
        intent_summary="test",
        required_nodes=required_nodes,
        trigger_node=trigger_node,
        workflow_name="Test",
        topology=None,
        user_description="test description",
    )


class TestExtractTopology:
    def test_positive_returns_topology_when_present(self):
        """Should return output.topology when it is populated."""
        output = _make_output()
        topo = _extract_topology(output)
        assert topo["entry_node"] == "Webhook"
        assert len(topo["nodes"]) == 2

    def test_positive_fallback_builds_linear_chain(self):
        """When topology is absent, fallback generates a linear chain."""
        output = _make_output_no_topology(["webhook", "slack"], "webhook")
        topo = _extract_topology(output)
        assert topo["entry_node"] in topo["nodes"]
        assert len(topo["edges"]) >= 1
        for edge in topo["edges"]:
            assert edge["branch"] is None

    def test_edge_trigger_node_inserted_when_missing_from_required(self):
        """Fallback inserts trigger_node at index 0 if not in required_nodes."""
        output = _make_output_no_topology(["slack"], "webhook")
        topo = _extract_topology(output)
        assert topo["nodes"][0] == "webhook"

    def test_contract_fallback_topology_shape(self):
        """Fallback topology must have nodes, edges, entry_node, branch_nodes."""
        output = _make_output_no_topology(["webhook", "slack"], "webhook")
        topo = _extract_topology(output)
        assert {"nodes", "edges", "entry_node", "branch_nodes"} <= set(topo.keys())
        assert topo["branch_nodes"] == []


class TestHandleCommit:
    def test_positive_returns_topology_in_state(self):
        """Commit with valid output must include topology key."""
        output = _make_output()
        decision = OrchestratorDecision(decision="commit", output=output)
        result = _handle_commit(decision)
        assert "topology" in result

    def test_positive_returns_user_description(self):
        """Commit result must include user_description."""
        output = _make_output()
        decision = OrchestratorDecision(decision="commit", output=output)
        result = _handle_commit(decision)
        assert "user_description" in result
        assert result["user_description"] == "Receive a webhook and post to Slack."

    def test_positive_orchestrator_decision_set_to_commit(self):
        """State key orchestrator_decision must be 'commit'."""
        decision = OrchestratorDecision(decision="commit", output=_make_output())
        result = _handle_commit(decision)
        assert result["orchestrator_decision"] == "commit"

    def test_negative_no_output_returns_default_plan(self):
        """Commit with output=None falls back to default required_nodes."""
        decision = OrchestratorDecision(decision="commit", output=None)
        result = _handle_commit(decision)
        assert result["orchestrator_decision"] == "commit"
        assert result.get("required_nodes") == ["webhook"]

    def test_edge_required_nodes_includes_trigger(self):
        """trigger_node is prepended to required_nodes if missing."""
        output = _make_output(
            required_nodes=["slack"],
            trigger_node="webhook",
        )
        decision = OrchestratorDecision(decision="commit", output=output)
        result = _handle_commit(decision)
        assert result["required_nodes"][0] == "webhook"

    def test_regression_topology_present_even_with_fallback(self):
        """Regression: topology must always be present in commit result."""
        output = _make_output_no_topology(["webhook", "slack"], "webhook")
        decision = OrchestratorDecision(decision="commit", output=output)
        result = _handle_commit(decision)
        assert "topology" in result
        assert isinstance(result["topology"], dict)


class TestExtractBlueprintFields:
    def test_positive_status_set_to_planning(self):
        """status field must be 'planning' after extracting blueprint fields."""
        output = _make_output()
        fields = _extract_blueprint_fields(output)
        assert fields["status"] == "planning"

    def test_contract_required_fields_present(self):
        """All four required keys must be in returned dict."""
        output = _make_output()
        fields = _extract_blueprint_fields(output)
        assert {"required_nodes", "topology", "user_description", "status"} <= set(fields.keys())


class TestHandleClarify:
    def test_positive_returns_clarify_decision(self):
        """Clarify handler sets orchestrator_decision to 'clarify'."""
        q = ClarifyingQuestion(question="Which Slack channel?", reason="needed for routing")
        decision = OrchestratorDecision(decision="clarify", clarification=q)
        result = _handle_clarify(decision)
        assert result["orchestrator_decision"] == "clarify"

    def test_positive_pending_question_propagated(self):
        """Question text appears in pending_question state key."""
        q = ClarifyingQuestion(question="Which Slack channel?", reason="needed")
        decision = OrchestratorDecision(decision="clarify", clarification=q)
        result = _handle_clarify(decision)
        assert result["pending_question"] == "Which Slack channel?"
