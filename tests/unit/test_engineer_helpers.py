"""Unit tests for _engineer_helpers: _branch_index and build_connections."""
import pytest
from types import SimpleNamespace
from src.agentic_system.build_cycle.nodes._engineer_helpers import (
    _branch_index,
    build_connections,
    merge_into_existing,
)

pytestmark = pytest.mark.unit


def _conn(source, target, branch=None, source_output=0, target_input=0):
    return SimpleNamespace(
        source=source, target=target, branch=branch,
        source_output=source_output, target_input=target_input,
    )


class TestBranchIndex:
    def test_positive_none_returns_0(self):
        assert _branch_index(None) == 0

    def test_positive_true_returns_0(self):
        assert _branch_index("true") == 0

    def test_positive_1_returns_0(self):
        assert _branch_index("1") == 0

    def test_positive_false_returns_1(self):
        assert _branch_index("false") == 1

    def test_positive_2_returns_1(self):
        assert _branch_index("2") == 1

    def test_positive_3_returns_2(self):
        assert _branch_index("3") == 2

    def test_negative_unknown_label_defaults_to_0(self):
        """Unknown branch label should fall back to index 0."""
        assert _branch_index("unknown") == 0


class TestBuildConnections:
    def test_positive_linear_connection_uses_main0(self):
        """branch=None → connection placed in main[0]."""
        conn = _conn("Webhook", "Slack", branch=None)
        result = build_connections([conn])
        assert len(result["Webhook"]["main"][0]) == 1
        assert result["Webhook"]["main"][0][0]["node"] == "Slack"

    def test_positive_false_branch_uses_main1(self):
        """branch='false' → connection placed in main[1]."""
        conn = _conn("If", "Gmail", branch="false")
        result = build_connections([conn])
        # main[0] is placeholder, main[1] has the target
        assert len(result["If"]["main"]) >= 2
        assert result["If"]["main"][1][0]["node"] == "Gmail"

    def test_positive_true_branch_uses_main0(self):
        """branch='true' → connection placed in main[0]."""
        conn = _conn("If", "Slack", branch="true")
        result = build_connections([conn])
        assert result["If"]["main"][0][0]["node"] == "Slack"

    def test_positive_multiple_outputs_from_same_source(self):
        """Two connections from same source populate both output slots."""
        conns = [
            _conn("If", "Slack", branch="true"),
            _conn("If", "Gmail", branch="false"),
        ]
        result = build_connections(conns)
        assert result["If"]["main"][0][0]["node"] == "Slack"
        assert result["If"]["main"][1][0]["node"] == "Gmail"

    def test_positive_source_output_override(self):
        """Non-zero source_output takes precedence over branch index."""
        conn = _conn("Switch", "NodeB", branch=None, source_output=2)
        result = build_connections([conn])
        assert len(result["Switch"]["main"]) >= 3
        assert result["Switch"]["main"][2][0]["node"] == "NodeB"

    def test_edge_empty_connections_list(self):
        """Empty list returns empty dict."""
        result = build_connections([])
        assert result == {}

    def test_contract_connection_entry_shape(self):
        """Each target entry must have node, type, index keys."""
        conn = _conn("Webhook", "Slack")
        result = build_connections([conn])
        entry = result["Webhook"]["main"][0][0]
        assert set(entry.keys()) == {"node", "type", "index"}
        assert entry["type"] == "main"


class TestMergeIntoExisting:
    def test_positive_new_nodes_appended(self):
        """New nodes not in existing are appended."""
        existing = {"nodes": [{"name": "Webhook", "id": "1"}], "connections": {}}
        new = {"nodes": [{"name": "Slack", "id": "2"}], "connections": {}}
        merged = merge_into_existing(existing, new)
        names = [n["name"] for n in merged["nodes"]]
        assert "Webhook" in names
        assert "Slack" in names

    def test_negative_duplicate_nodes_not_added(self):
        """Nodes already present in existing are not duplicated."""
        node = {"name": "Webhook", "id": "1"}
        existing = {"nodes": [node], "connections": {}}
        new = {"nodes": [{"name": "Webhook", "id": "2"}], "connections": {}}
        merged = merge_into_existing(existing, new)
        assert len([n for n in merged["nodes"] if n["name"] == "Webhook"]) == 1

    def test_positive_connections_merged(self):
        """New connections for a new source are added to merged result."""
        existing = {"nodes": [], "connections": {"Webhook": {"main": [[{"node": "Slack", "type": "main", "index": 0}]]}}}
        new = {"nodes": [], "connections": {"Slack": {"main": [[{"node": "Gmail", "type": "main", "index": 0}]]}}}
        merged = merge_into_existing(existing, new)
        assert "Slack" in merged["connections"]
        assert "Webhook" in merged["connections"]
