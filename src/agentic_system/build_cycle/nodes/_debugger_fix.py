"""Debugger — fix application + helpers."""
from __future__ import annotations

import uuid

from langchain_core.messages import HumanMessage


def _apply_full_fix(workflow_json: dict, result: dict) -> dict:
    """Apply all fix operations to the workflow JSON."""
    patched = dict(workflow_json)
    nodes = list(patched.get("nodes", []))

    if result.get("removed_node_names"):
        removed = set(result["removed_node_names"])
        nodes = [n for n in nodes if n.get("name") not in removed]

    if result.get("fixed_nodes"):
        for fix in result["fixed_nodes"]:
            for i, node in enumerate(nodes):
                if node.get("name") == fix["node_name"]:
                    nodes[i] = _patch_node(node, fix)
                    break

    if result.get("added_nodes"):
        for new_node in result["added_nodes"]:
            nodes.append({
                "id": str(uuid.uuid4()),
                "name": new_node["name"],
                "type": new_node["type"],
                "typeVersion": 1,
                "position": new_node["position"],
                "parameters": new_node["parameters"],
                **({"credentials": new_node["credentials"]} if new_node.get("credentials") else {}),
            })

    patched["nodes"] = nodes

    if result.get("fixed_connections"):
        patched["connections"] = result["fixed_connections"]

    return patched


def _patch_node(node: dict, fix: dict) -> dict:
    """Apply a fix patch to an existing node dict."""
    patched = dict(node)
    patched["parameters"] = fix["parameters"]
    if fix.get("new_type"):
        patched["type"] = fix["new_type"]
    if fix.get("credentials"):
        patched["credentials"] = fix["credentials"]
    return patched


def _has_any_fix(result: dict) -> bool:
    """Check if the result contains any fix operations."""
    return any([
        result.get("fixed_nodes"),
        bool(result.get("fixed_connections")),
        result.get("added_nodes"),
        result.get("removed_node_names"),
    ])


def _describe_fix(result: dict) -> str:
    """Human-readable summary of what the fix changed."""
    parts = []
    if result.get("fixed_nodes"):
        parts.append(f"patched {len(result['fixed_nodes'])} node(s)")
    if result.get("added_nodes"):
        parts.append(f"added {len(result['added_nodes'])} node(s)")
    if result.get("removed_node_names"):
        parts.append(f"removed {len(result['removed_node_names'])} node(s)")
    if result.get("fixed_connections"):
        parts.append("rewired connections")
    return ", ".join(parts) if parts else "no changes"


def _build_fix_updates(
    workflow_json: dict, result: dict, error_data: dict, fix_attempts: int,
) -> dict:
    """Assemble the state update dict from a debugger result."""
    classified = {
        "type": result["error_type"],
        "node_name": result["node_name"],
        "message": result["message"],
        "description": result.get("description"),
        "line_number": None,
        "stack": error_data.get("stack"),
    }

    updates: dict = {
        "classified_error": classified,
        "fix_attempts": fix_attempts + 1,
        "messages": [HumanMessage(
            content=f"[Debugger] {result['error_type']} in '{result['node_name']}': {result['message']}"
        )],
    }

    if _has_any_fix(result):
        updates["workflow_json"] = _apply_full_fix(workflow_json, result)
        updates["status"] = "building"
        updates["messages"].append(HumanMessage(
            content=f"[Debugger] Fix applied — {_describe_fix(result)}"
        ))

    return updates
