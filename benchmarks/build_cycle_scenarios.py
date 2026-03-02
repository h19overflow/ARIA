"""Complex benchmark scenarios for ARIA build cycle stress testing.

Each scenario is an ARIAState-compatible dict following the format from
test_build_cycle_real.py, extended with topology and expected metadata.

Usage:
    from benchmarks.build_cycle_scenarios import BENCHMARK_SCENARIOS, make_build_state
"""
from __future__ import annotations

from benchmarks.scenario_definitions import (
    SCENARIO_1_MULTI_BRANCH,
    SCENARIO_2_TRANSFORM_CHAIN,
    SCENARIO_3_FAN_OUT_SWITCH,
)


def make_build_state(scenario: dict) -> dict:
    """Convert a benchmark scenario to an ARIAState-compatible dict."""
    bp = scenario["blueprint"]
    topo = bp.get("topology")
    return {
        "messages": [],
        "intent": bp["intent"],
        "required_nodes": bp["required_nodes"],
        "resolved_credential_ids": bp.get("credential_ids", {}),
        "pending_credential_types": [],
        "build_blueprint": bp,
        "node_templates": [],
        "workflow_json": None,
        "n8n_workflow_id": None,
        "n8n_execution_id": None,
        "execution_result": None,
        "classified_error": None,
        "fix_attempts": 0,
        "webhook_url": None,
        "status": "building",
        "topology": topo,
        "user_description": bp.get("user_description", bp["intent"]),
    }


BENCHMARK_SCENARIOS = [
    SCENARIO_1_MULTI_BRANCH,
    SCENARIO_2_TRANSFORM_CHAIN,
    SCENARIO_3_FAN_OUT_SWITCH,
]
