"""Helper functions for the Engineer node -- payload building and merging."""
from __future__ import annotations

import uuid

from src.agentic_system.build_cycle.schemas.workflow import EngineerOutput


def to_n8n_payload(output: EngineerOutput, cred_ids: dict[str, str]) -> dict:
    """Convert EngineerOutput to n8n POST /workflows body."""
    nodes = [_build_node(node, i) for i, node in enumerate(output.nodes)]
    connections = build_connections(output.connections)

    return {
        "name": output.workflow_name,
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
    }


def _build_node(node: object, index: int) -> dict:
    """Build a single n8n node dict from an EngineerOutput node."""
    n8n_node: dict = {
        "id": str(uuid.uuid4()),
        "name": node.name,
        "type": node.type,
        "parameters": node.parameters,
        "position": [250 * index, 300],
        "typeVersion": 1,
    }
    if "webhook" in node.type.lower():
        n8n_node["webhookId"] = str(uuid.uuid4())
    if node.credentials:
        n8n_node["credentials"] = node.credentials
    return n8n_node


def _branch_index(branch: str | None) -> int:
    """Convert branch label to n8n output index.

    'true' / '1' → 0, 'false' / '2' → 1, '3' → 2, None → 0
    """
    if branch in (None, "true", "1"):
        return 0
    if branch in ("false", "2"):
        return 1
    if branch == "3":
        return 2
    return 0


def build_connections(connections: list) -> dict:
    """Build n8n connections dict from WorkflowConnection list."""
    result: dict = {}
    for conn in connections:
        source_entry = result.setdefault(conn.source, {"main": [[]]})
        output_idx = _branch_index(getattr(conn, "branch", None))
        # source_output takes precedence when set (non-zero)
        if getattr(conn, "source_output", 0):
            output_idx = conn.source_output
        while len(source_entry["main"]) <= output_idx:
            source_entry["main"].append([])
        source_entry["main"][output_idx].append({
            "node": conn.target,
            "type": "main",
            "index": conn.target_input,
        })
    return result


def merge_into_existing(existing: dict, new: dict) -> dict:
    """Merge new phase nodes/connections into existing workflow."""
    merged = dict(existing)
    existing_names = {n["name"] for n in merged.get("nodes", [])}

    merged["nodes"] = _merge_nodes(merged.get("nodes", []), new.get("nodes", []), existing_names)
    merged["connections"] = _merge_connections(
        merged.get("connections", {}), new.get("connections", {}),
    )
    return merged


def _merge_nodes(
    existing_nodes: list[dict], new_nodes: list[dict], existing_names: set[str],
) -> list[dict]:
    """Add new nodes to existing list, skipping duplicates."""
    merged = list(existing_nodes)
    for node in new_nodes:
        if node["name"] not in existing_names:
            node["position"] = [250 * len(merged), 300]
            merged.append(node)
    return merged


def _merge_connections(existing_conns: dict, new_conns: dict) -> dict:
    """Merge new connections into existing connections dict."""
    merged = dict(existing_conns)
    for source, data in new_conns.items():
        if source not in merged:
            merged[source] = data
        else:
            _append_new_targets(merged[source], data)
    return merged


def _append_new_targets(existing_entry: dict, new_entry: dict) -> None:
    """Append targets from new_entry that don't exist in existing_entry."""
    for out_idx, targets in enumerate(new_entry.get("main", [])):
        while len(existing_entry["main"]) <= out_idx:
            existing_entry["main"].append([])
        existing_targets = {t["node"] for t in existing_entry["main"][out_idx]}
        for target in targets:
            if target["node"] not in existing_targets:
                existing_entry["main"][out_idx].append(target)
