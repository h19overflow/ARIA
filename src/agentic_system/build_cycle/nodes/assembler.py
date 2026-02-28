"""Fan-in node: collect parallel worker results and assemble final n8n workflow JSON."""
from __future__ import annotations

import logging
import time

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.services.pipeline.event_bus import get_event_bus

logger = logging.getLogger(__name__)


def _branch_index(branch: str | None) -> int:
    """Convert branch label to n8n output index. None/'true'/'1' → 0, 'false'/'2' → 1, '3' → 2."""
    if branch in (None, "true", "1"):
        return 0
    if branch in ("false", "2"):
        return 1
    if branch == "3":
        return 2
    return 0


async def assembler_node(state: ARIAState) -> dict:
    """Collect all node_build_results, validate, then assemble workflow JSON."""
    bus = get_event_bus(state)
    if bus:
        await bus.emit_start("assemble", "Assembler", "Assembling workflow...")
    start = time.monotonic()

    results = state.get("node_build_results", [])
    failed = _find_failed_results(results)

    if failed:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete(
                "assemble", "Assembler", "error",
                f"{len(failed)} node(s) failed validation", duration_ms=elapsed,
            )
        return _build_validation_failure_output(failed)

    planned_edges: list[dict] = state.get("planned_edges", [])
    node_names = {r["node_name"] for r in results}

    dangling_error = _find_dangling_edge(planned_edges, node_names)
    if dangling_error:
        elapsed = int((time.monotonic() - start) * 1000)
        if bus:
            await bus.emit_complete("assemble", "Assembler", "error", dangling_error, duration_ms=elapsed)
        return _build_edge_error_output(dangling_error)

    workflow_name = _resolve_workflow_name(state)
    connections = _build_connections_from_edges(planned_edges, node_names)
    workflow_json = _assemble_workflow_json(workflow_name, results, connections)

    elapsed = int((time.monotonic() - start) * 1000)
    if bus:
        await bus.emit_complete(
            "assemble", "Assembler", "success",
            f"Assembled {len(results)} nodes", duration_ms=elapsed,
        )

    logger.info("[Assembler] Assembled %d nodes into workflow '%s'.", len(results), workflow_name)
    return {
        "workflow_json": workflow_json,
        "status": "building",
        "messages": [HumanMessage(content=f"[Assembler] Assembled {len(results)} nodes into workflow.")],
    }


def _find_failed_results(results: list[dict]) -> list[dict]:
    """Return results where validation did not pass."""
    return [r for r in results if not r.get("validation_passed", False)]


def _find_dangling_edge(planned_edges: list[dict], node_names: set[str]) -> str | None:
    """Return an error message if any edge references a node not in node_names."""
    for edge in planned_edges:
        source = edge.get("from_node", "")
        target = edge.get("to_node", "")
        if source not in node_names:
            return f"Edge references unknown source node '{source}'"
        if target not in node_names:
            return f"Edge references unknown target node '{target}'"
    return None


def _build_connections_from_edges(planned_edges: list[dict], node_names: set[str]) -> dict:
    """Convert planned edges to n8n connections format."""
    connections: dict = {}
    for edge in planned_edges:
        source = edge["from_node"]
        target = edge["to_node"]
        branch = edge.get("branch")

        source_entry = connections.setdefault(source, {"main": [[]]})
        output_idx = _branch_index(branch)
        while len(source_entry["main"]) <= output_idx:
            source_entry["main"].append([])
        source_entry["main"][output_idx].append({"node": target, "type": "main", "index": 0})
    return connections


def _resolve_workflow_name(state: ARIAState) -> str:
    """Extract workflow name from state or return a safe default."""
    blueprint = state.get("build_blueprint") or {}
    intent = blueprint.get("intent") or state.get("intent") or ""
    return intent[:60] if intent else "ARIA Workflow"


def _assemble_workflow_json(
    workflow_name: str,
    results: list[dict],
    connections: dict,
) -> dict:
    """Build the final n8n workflow payload from assembled parts."""
    return {
        "name": workflow_name,
        "nodes": [r["node_json"] for r in results],
        "connections": connections,
        "settings": {"executionOrder": "v1"},
    }


def _build_validation_failure_output(failed: list[dict]) -> dict:
    """Build the state patch that short-circuits to the debugger."""
    error_messages: list[str] = []
    for failed_result in failed:
        error_messages.extend(failed_result.get("validation_errors", []))

    first_node_name = failed[0].get("node_name", "unknown")
    summary = f"{len(failed)} node(s) failed validation: {'; '.join(error_messages[:3])}"

    logger.warning("[Assembler] Validation gate failed — %s", summary)
    return {
        "status": "fixing",
        "classified_error": {
            "type": "schema",
            "node_name": first_node_name,
            "message": summary,
            "description": None,
            "line_number": None,
            "stack": None,
        },
        "messages": [HumanMessage(content=f"[Assembler] {len(failed)} node(s) failed. Routing to debugger.")],
    }


def _build_edge_error_output(error_message: str) -> dict:
    """Build the state patch for a dangling edge error."""
    logger.warning("[Assembler] Edge validation failed — %s", error_message)
    return {
        "status": "fixing",
        "classified_error": {
            "type": "schema",
            "node_name": "unknown",
            "message": error_message,
            "description": None,
            "line_number": None,
            "stack": None,
        },
        "messages": [HumanMessage(content=f"[Assembler] Edge error: {error_message}. Routing to debugger.")],
    }
