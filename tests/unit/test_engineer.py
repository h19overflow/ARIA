"""Unit tests for engineer prompt-building helpers."""
import pytest
from src.agentic_system.build_cycle.nodes.engineer import (
    _build_phase_prompt,
    _build_topology_block,
    _filter_templates,
    _template_matches,
)

pytestmark = pytest.mark.unit

_BLUEPRINT = {"intent": "send a Slack notification", "topology": {}}


def _make_entry(nodes, internal_edges, entry_edges):
    return {"nodes": nodes, "internal_edges": internal_edges, "entry_edges": entry_edges}


class TestBuildTopologyBlock:
    def test_positive_entry_edge_appears_with_existing_label(self):
        """Should label the source node as EXISTING when entry_edges present."""
        entry = _make_entry(
            ["Slack"],
            [],
            [{"from_node": "Webhook", "to_node": "Slack", "branch": None}],
        )
        block = _build_topology_block(1, entry)
        assert "Webhook (EXISTING)" in block

    def test_positive_entry_edge_uses_main_label_for_none_branch(self):
        """branch=None should render as [main] in block."""
        entry = _make_entry(
            ["Slack"], [],
            [{"from_node": "Webhook", "to_node": "Slack", "branch": None}],
        )
        block = _build_topology_block(1, entry)
        assert "--[main]-->" in block

    def test_positive_branch_label_preserved(self):
        """branch='true' should render as [true] in block."""
        entry = _make_entry(
            ["Slack"], [],
            [{"from_node": "If", "to_node": "Slack", "branch": "true"}],
        )
        block = _build_topology_block(1, entry)
        assert "--[true]-->" in block

    def test_positive_false_branch_label(self):
        """branch='false' should render as [false] in block."""
        entry = _make_entry(
            ["Gmail"], [],
            [{"from_node": "If", "to_node": "Gmail", "branch": "false"}],
        )
        block = _build_topology_block(1, entry)
        assert "--[false]-->" in block

    def test_positive_internal_edges_rendered(self):
        """Internal edges should appear under their own section."""
        entry = _make_entry(
            ["If", "Set"],
            [{"from_node": "If", "to_node": "Set", "branch": "true"}],
            [],
        )
        block = _build_topology_block(1, entry)
        assert "If" in block
        assert "Set" in block

    def test_negative_phase0_no_entry_edges_no_connection_map_missing(self):
        """Phase 0 with no edges still emits Connection Map header."""
        entry = _make_entry(["Webhook"], [], [])
        block = _build_topology_block(0, entry)
        # header is always emitted but no entry/internal sections
        assert "Connection Map" in block
        assert "EXISTING" not in block


class TestBuildPhasePrompt:
    def test_positive_prompt_contains_intent(self):
        """Prompt must include the blueprint intent."""
        entry = _make_entry(["Webhook"], [], [])
        prompt = _build_phase_prompt(_BLUEPRINT, [], {}, 0, entry, None)
        assert "send a Slack notification" in prompt

    def test_positive_prompt_contains_phase_number(self):
        """Prompt must include the current phase number."""
        entry = _make_entry(["Slack"], [], [{"from_node": "Webhook", "to_node": "Slack", "branch": None}])
        prompt = _build_phase_prompt(_BLUEPRINT, [], {}, 1, entry, None)
        assert "Phase: 1" in prompt

    def test_positive_existing_workflow_block_when_phase_gt0(self):
        """Existing workflow JSON appended only for phase > 0."""
        entry = _make_entry(["Slack"], [], [])
        existing = {"nodes": [], "connections": {}}
        prompt = _build_phase_prompt(_BLUEPRINT, [], {}, 1, entry, existing)
        assert "DO NOT recreate" in prompt

    def test_negative_no_existing_block_for_phase0(self):
        """Existing workflow block must NOT appear for phase 0."""
        entry = _make_entry(["Webhook"], [], [])
        existing = {"nodes": [], "connections": {}}
        prompt = _build_phase_prompt(_BLUEPRINT, [], {}, 0, entry, existing)
        assert "DO NOT recreate" not in prompt

    def test_edge_empty_templates_still_produces_prompt(self):
        """Empty templates list should not raise."""
        entry = _make_entry(["Webhook"], [], [])
        prompt = _build_phase_prompt(_BLUEPRINT, [], {}, 0, entry, None)
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestFilterTemplates:
    def test_positive_matching_template_included(self):
        """Template whose node_type matches phase node is included."""
        templates = [{"node_type": "slackNode"}, {"node_type": "gmailNode"}]
        result = _filter_templates(templates, ["Slack"])
        assert len(result) == 1
        assert result[0]["node_type"] == "slackNode"

    def test_negative_non_matching_template_excluded(self):
        """Template not matching any phase node is excluded."""
        templates = [{"node_type": "gmailNode"}]
        result = _filter_templates(templates, ["Slack"])
        assert result == []

    def test_edge_empty_templates(self):
        """Empty template list returns empty list."""
        assert _filter_templates([], ["Slack"]) == []
