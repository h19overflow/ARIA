# tests/unit/test_benchmark_scenarios.py
"""Validate benchmark scenario structure and topology integrity."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from benchmarks.build_cycle_scenarios import BENCHMARK_SCENARIOS, make_build_state


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s["name"])
def test_scenario_has_required_fields(scenario):
    assert "name" in scenario
    assert "blueprint" in scenario
    assert "expected" in scenario
    bp = scenario["blueprint"]
    assert "intent" in bp
    assert "required_nodes" in bp
    assert "credential_ids" in bp
    assert "topology" in bp


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s["name"])
def test_topology_edges_reference_valid_nodes(scenario):
    topo = scenario["blueprint"]["topology"]
    node_names = set(topo["nodes"])
    for edge in topo["edges"]:
        assert edge["from_node"] in node_names, (
            f"Edge from_node '{edge['from_node']}' not in nodes: {node_names}"
        )
        assert edge["to_node"] in node_names, (
            f"Edge to_node '{edge['to_node']}' not in nodes: {node_names}"
        )


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s["name"])
def test_entry_node_exists_and_has_no_incoming_edges(scenario):
    topo = scenario["blueprint"]["topology"]
    assert topo["entry_node"] in topo["nodes"]
    incoming = [e["to_node"] for e in topo["edges"]]
    assert topo["entry_node"] not in incoming, (
        f"Entry node '{topo['entry_node']}' has incoming edges"
    )


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s["name"])
def test_expected_counts_match(scenario):
    topo = scenario["blueprint"]["topology"]
    expected = scenario["expected"]
    assert len(topo["nodes"]) == expected["node_count"]
    assert len(topo["edges"]) == expected["edge_count"]


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s["name"])
def test_branch_nodes_have_multiple_outbound_edges(scenario):
    topo = scenario["blueprint"]["topology"]
    for branch_node in topo["branch_nodes"]:
        outbound = [e for e in topo["edges"] if e["from_node"] == branch_node]
        assert len(outbound) >= 2, (
            f"Branch node '{branch_node}' has only {len(outbound)} outbound edges"
        )


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s["name"])
def test_make_build_state_produces_valid_dict(scenario):
    state = make_build_state(scenario)
    assert state["intent"] == scenario["blueprint"]["intent"]
    assert state["status"] == "building"
    assert state["topology"] == scenario["blueprint"]["topology"]
    assert isinstance(state["messages"], list)
