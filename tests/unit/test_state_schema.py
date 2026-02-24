"""Unit tests for state.py TypedDicts: WorkflowEdge, WorkflowTopology, PhaseEntry, BuildBlueprint."""
import pytest
from src.agentic_system.shared.state import (
    WorkflowEdge,
    WorkflowTopology,
    PhaseEntry,
    BuildBlueprint,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# WorkflowEdge
# ---------------------------------------------------------------------------

class TestWorkflowEdge:
    def test_positive_linear_edge(self):
        """Should instantiate a linear edge with branch=None."""
        edge: WorkflowEdge = {"from_node": "Webhook", "to_node": "Slack", "branch": None}
        assert edge["from_node"] == "Webhook"
        assert edge["to_node"] == "Slack"
        assert edge["branch"] is None

    def test_positive_branch_edge(self):
        """Should instantiate a branching edge with branch label."""
        edge: WorkflowEdge = {"from_node": "If", "to_node": "Gmail", "branch": "false"}
        assert edge["branch"] == "false"

    def test_edge_contract_required_keys(self):
        """Contract: WorkflowEdge must contain from_node, to_node, branch."""
        edge: WorkflowEdge = {"from_node": "A", "to_node": "B", "branch": "true"}
        assert set(edge.keys()) == {"from_node", "to_node", "branch"}


# ---------------------------------------------------------------------------
# WorkflowTopology
# ---------------------------------------------------------------------------

class TestWorkflowTopology:
    def test_positive_full_topology(self):
        """Should instantiate with all required fields populated."""
        topo: WorkflowTopology = {
            "nodes": ["Webhook", "Slack"],
            "edges": [{"from_node": "Webhook", "to_node": "Slack", "branch": None}],
            "entry_node": "Webhook",
            "branch_nodes": [],
        }
        assert topo["entry_node"] == "Webhook"
        assert len(topo["nodes"]) == 2
        assert topo["branch_nodes"] == []

    def test_positive_with_branch_nodes(self):
        """Should accept branch_nodes list."""
        topo: WorkflowTopology = {
            "nodes": ["Webhook", "If", "Slack", "Gmail"],
            "edges": [],
            "entry_node": "Webhook",
            "branch_nodes": ["If"],
        }
        assert "If" in topo["branch_nodes"]

    def test_edge_empty_topology(self):
        """Edge: should accept empty nodes and edges lists."""
        topo: WorkflowTopology = {"nodes": [], "edges": [], "entry_node": "Webhook", "branch_nodes": []}
        assert topo["nodes"] == []

    def test_contract_required_keys(self):
        """Contract: topology must have nodes, edges, entry_node, branch_nodes."""
        topo: WorkflowTopology = {
            "nodes": [], "edges": [], "entry_node": "X", "branch_nodes": [],
        }
        assert {"nodes", "edges", "entry_node", "branch_nodes"} <= set(topo.keys())


# ---------------------------------------------------------------------------
# PhaseEntry
# ---------------------------------------------------------------------------

class TestPhaseEntry:
    def test_positive_phase_with_edges(self):
        """Should instantiate a phase entry with all edge lists."""
        phase: PhaseEntry = {
            "nodes": ["Slack"],
            "internal_edges": [],
            "entry_edges": [{"from_node": "Webhook", "to_node": "Slack", "branch": None}],
        }
        assert phase["nodes"] == ["Slack"]
        assert len(phase["entry_edges"]) == 1

    def test_positive_first_phase_no_entry_edges(self):
        """First phase should have empty entry_edges."""
        phase: PhaseEntry = {"nodes": ["Webhook"], "internal_edges": [], "entry_edges": []}
        assert phase["entry_edges"] == []

    def test_contract_required_keys(self):
        """Contract: PhaseEntry must have nodes, internal_edges, entry_edges."""
        phase: PhaseEntry = {"nodes": [], "internal_edges": [], "entry_edges": []}
        assert {"nodes", "internal_edges", "entry_edges"} <= set(phase.keys())


# ---------------------------------------------------------------------------
# BuildBlueprint
# ---------------------------------------------------------------------------

class TestBuildBlueprint:
    def test_positive_full_blueprint(self):
        """Should instantiate with topology and user_description keys."""
        bp: BuildBlueprint = {
            "intent": "send a slack message",
            "required_nodes": ["webhook", "slack"],
            "credential_ids": {"slack": "cred-123"},
            "topology": {
                "nodes": ["Webhook", "Slack"],
                "edges": [{"from_node": "Webhook", "to_node": "Slack", "branch": None}],
                "entry_node": "Webhook",
                "branch_nodes": [],
            },
            "user_description": "Receive a webhook and post to Slack.",
        }
        assert "topology" in bp
        assert "user_description" in bp
        assert bp["user_description"] == "Receive a webhook and post to Slack."

    def test_contract_topology_and_description_keys(self):
        """Contract: BuildBlueprint must expose topology and user_description."""
        bp: BuildBlueprint = {
            "intent": "x",
            "required_nodes": [],
            "credential_ids": {},
            "topology": {"nodes": [], "edges": [], "entry_node": "w", "branch_nodes": []},
            "user_description": "desc",
        }
        assert "topology" in bp
        assert "user_description" in bp
