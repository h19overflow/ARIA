"""Unit tests for the BFS phase planner."""
import pytest
from src.agentic_system.build_cycle.nodes.phase_planner import (
    _build_phases_from_topology,
    _bfs_assign_phases,
    _attach_edges,
    _fallback_phases,
    _is_logic_node,
    phase_planner_node,
)

pytestmark = pytest.mark.unit

LINEAR_TOPOLOGY = {
    "nodes": ["Webhook", "Slack", "Gmail"],
    "edges": [
        {"from_node": "Webhook", "to_node": "Slack", "branch": None},
        {"from_node": "Slack", "to_node": "Gmail", "branch": None},
    ],
    "entry_node": "Webhook",
    "branch_nodes": [],
}

BRANCH_TOPOLOGY = {
    "nodes": ["Webhook", "If", "Slack", "Gmail"],
    "edges": [
        {"from_node": "Webhook", "to_node": "If", "branch": None},
        {"from_node": "If", "to_node": "Slack", "branch": "true"},
        {"from_node": "If", "to_node": "Gmail", "branch": "false"},
    ],
    "entry_node": "Webhook",
    "branch_nodes": ["If"],
}


class TestBfsAssignPhases:
    def test_positive_linear_produces_three_buckets(self):
        """Linear chain of 3 nodes → 3 phase buckets."""
        buckets = _bfs_assign_phases(LINEAR_TOPOLOGY)
        assert len(buckets) == 3
        assert buckets[0] == ["Webhook"]
        assert buckets[1] == ["Slack"]
        assert buckets[2] == ["Gmail"]

    def test_positive_branch_topology_buckets(self):
        """Branch topology: If is a logic node, groups with adjacent nodes."""
        buckets = _bfs_assign_phases(BRANCH_TOPOLOGY)
        all_nodes = [n for bucket in buckets for n in bucket]
        assert "Webhook" in all_nodes
        assert "If" in all_nodes
        assert "Slack" in all_nodes
        assert "Gmail" in all_nodes

    def test_edge_single_node(self):
        """Topology with a single node → 1 bucket."""
        topo = {"nodes": ["Webhook"], "edges": [], "entry_node": "Webhook", "branch_nodes": []}
        buckets = _bfs_assign_phases(topo)
        assert buckets == [["Webhook"]]


class TestAttachEdges:
    def test_positive_phase0_no_entry_edges(self):
        """Phase 0 should always have empty entry_edges."""
        phases = _build_phases_from_topology(LINEAR_TOPOLOGY)
        assert phases[0]["entry_edges"] == []
        assert phases[0]["nodes"] == ["Webhook"]

    def test_positive_phase1_entry_edge_from_webhook(self):
        """Phase 1 entry_edges must contain the Webhook→Slack edge."""
        phases = _build_phases_from_topology(LINEAR_TOPOLOGY)
        entry = phases[1]["entry_edges"]
        assert len(entry) == 1
        assert entry[0]["from_node"] == "Webhook"
        assert entry[0]["to_node"] == "Slack"

    def test_positive_phase2_entry_edge_branch_preserved(self):
        """Branch label must be preserved in entry_edges."""
        phases = _build_phases_from_topology(BRANCH_TOPOLOGY)
        all_entry = [e for p in phases for e in p["entry_edges"]]
        branches = {e["branch"] for e in all_entry}
        assert "true" in branches or "false" in branches

    def test_positive_internal_edges_empty_for_single_node_phases(self):
        """Each single-node phase has no internal edges."""
        phases = _build_phases_from_topology(LINEAR_TOPOLOGY)
        for phase in phases:
            assert phase["internal_edges"] == []

    def test_contract_phase_entry_structure(self):
        """Every PhaseEntry must have nodes, internal_edges, entry_edges."""
        phases = _build_phases_from_topology(LINEAR_TOPOLOGY)
        for phase in phases:
            assert "nodes" in phase
            assert "internal_edges" in phase
            assert "entry_edges" in phase


class TestFallbackPhases:
    def test_positive_fallback_produces_phase_per_node(self):
        """Fallback: N required_nodes → N PhaseEntry dicts."""
        phases = _fallback_phases(["webhook", "slack", "gmail"])
        assert len(phases) == 3

    def test_positive_fallback_first_node_trigger(self):
        """First phase in fallback must be the trigger node."""
        phases = _fallback_phases(["webhook", "slack"])
        assert phases[0]["nodes"] == ["webhook"]

    def test_edge_fallback_no_edges(self):
        """Fallback phases have empty edge lists."""
        phases = _fallback_phases(["webhook", "slack"])
        for phase in phases:
            assert phase["internal_edges"] == []
            assert phase["entry_edges"] == []


class TestIsLogicNode:
    def test_positive_if_is_logic(self):
        assert _is_logic_node("if") is True

    def test_positive_switch_is_logic(self):
        assert _is_logic_node("switch") is True

    def test_negative_webhook_not_logic(self):
        assert _is_logic_node("Webhook") is False

    def test_negative_slack_not_logic(self):
        assert _is_logic_node("Slack") is False


class TestPhasePlannerNode:
    @pytest.mark.asyncio
    async def test_positive_with_topology_in_blueprint(self):
        """Node returns phase_node_map list when topology present in blueprint."""
        state = {
            "build_blueprint": {"topology": LINEAR_TOPOLOGY},
            "required_nodes": [],
        }
        result = await phase_planner_node(state)
        assert isinstance(result["phase_node_map"], list)
        assert result["total_phases"] == 3
        assert result["build_phase"] == 0

    @pytest.mark.asyncio
    async def test_positive_fallback_when_no_topology(self):
        """Node falls back to required_nodes when topology absent."""
        state = {
            "build_blueprint": {},
            "required_nodes": ["webhook", "slack"],
        }
        result = await phase_planner_node(state)
        phases = result["phase_node_map"]
        assert isinstance(phases, list)
        assert all(isinstance(p, dict) for p in phases)
        assert all("nodes" in p for p in phases)

    @pytest.mark.asyncio
    async def test_edge_empty_state_returns_empty_plan(self):
        """Node returns empty plan when no topology and no required_nodes."""
        state = {"build_blueprint": {}, "required_nodes": []}
        result = await phase_planner_node(state)
        assert result["phase_node_map"] == []
        assert result["total_phases"] == 0
