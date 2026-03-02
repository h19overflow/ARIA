"""Debugger — workflow compaction for prompt context."""
from __future__ import annotations


def _summarize_workflow(workflow_json: dict, failing_node_name: str | None) -> dict:
    """Compact workflow for the debugger prompt.

    The failing node keeps full parameters (the LLM needs them to produce a fix).
    All other nodes are summarised to name/type/credentials only.
    Connections are compacted to simple edge lists to avoid massive JSON blobs.
    """
    summary = {
        k: v for k, v in workflow_json.items()
        if k not in ("nodes", "connections")
    }
    summary["nodes"] = _compact_nodes(workflow_json, failing_node_name)
    summary["connections"] = _compact_connections(workflow_json.get("connections", {}))
    return summary


def _compact_nodes(workflow_json: dict, failing_node_name: str | None) -> list[dict]:
    """Keep full params for the failing node, summarise all others."""
    compact: list[dict] = []
    for node in workflow_json.get("nodes", []):
        if node.get("name") == failing_node_name:
            compact.append(node)
        else:
            short: dict = {
                "name": node.get("name"),
                "type": node.get("type"),
            }
            if node.get("credentials"):
                short["credentials"] = node["credentials"]
            compact.append(short)
    return compact


def _compact_connections(connections: dict) -> dict:
    """Reduce n8n connections to simple edge list format.

    Turns ``{A: {main: [[{node: B, type: main, index: 0}]]}}``
    into ``{A: {main: [[{node: B}]]}}``, dropping redundant type/index fields.
    """
    compact: dict = {}
    for source, outputs in connections.items():
        compact_outputs: dict = {}
        for output_key, branches in outputs.items():
            compact_branches = []
            for branch in branches:
                compact_branches.append([
                    {"node": edge["node"]} for edge in branch if "node" in edge
                ])
            compact_outputs[output_key] = compact_branches
        compact[source] = compact_outputs
    return compact
