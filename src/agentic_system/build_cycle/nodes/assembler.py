"""Fan-in node: collect parallel worker results and assemble final n8n workflow JSON.

Uses an LLM agent with search_n8n_nodes to build correct connections,
especially for branching nodes (If, Switch, Router).
"""
from __future__ import annotations

import json
import logging
import time

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.schemas.node_plan import AssemblerOutput
from src.agentic_system.build_cycle.prompts.assembler import ASSEMBLER_SYSTEM_PROMPT
from src.agentic_system.build_cycle.tools import search_n8n_nodes
from src.services.pipeline.event_bus import get_event_bus

logger = logging.getLogger(__name__)

_agent = BaseAgent[AssemblerOutput](
    prompt=ASSEMBLER_SYSTEM_PROMPT,
    schema=AssemblerOutput,
    name="Assembler",
    tools=[search_n8n_nodes],
    recursion_limit=20,
)


async def assembler_node(state: ARIAState) -> dict:
    """Collect all node_build_results, validate, then assemble workflow JSON."""
    bus = get_event_bus(state)
    if bus:
        await bus.emit_start("assemble", "Assembler", "Assembling workflow...")
    start = time.monotonic()

    results = state.get("node_build_results", [])
    failed = _find_failed_results(results)

    if failed:
        return await _emit_and_return_error(bus, start, _build_validation_failure_output(failed))

    planned_edges: list[dict] = state.get("planned_edges", [])
    node_names = {r["node_name"] for r in results}

    dangling_error = _find_dangling_edge(planned_edges, node_names)
    if dangling_error:
        return await _emit_and_return_error(bus, start, _build_edge_error_output(dangling_error))

    node_list = _extract_node_list(results)
    connections = await _build_connections_via_agent(planned_edges, node_list)

    conn_error = _validate_connections(connections, planned_edges, node_list)
    if conn_error:
        return await _emit_and_return_error(bus, start, _build_edge_error_output(conn_error))

    workflow_name = _resolve_workflow_name(state)
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


# ── Agent invocation ─────────────────────────────────────────────────────────

async def _build_connections_via_agent(
    planned_edges: list[dict],
    node_list: list[dict],
) -> dict:
    """Invoke the Assembler agent to produce the n8n connections object.

    Falls back to deterministic wiring if the LLM returns empty connections.
    """
    prompt = _build_assembler_prompt(planned_edges, node_list)
    output: AssemblerOutput = await _agent.invoke([HumanMessage(content=prompt)])
    connections = _convert_assembler_output_to_dict(output)
    if connections:
        logger.info("[Assembler] LLM produced connections for %d sources", len(connections))
        return connections

    logger.warning("[Assembler] LLM returned empty connections — using deterministic fallback")
    return _build_connections_from_edges(planned_edges)


def _convert_assembler_output_to_dict(output: AssemblerOutput) -> dict:
    """Convert list-based AssemblerOutput to n8n connections dict."""
    result: dict = {}
    for entry in output.connections:
        result[entry.source_node_name] = {
            "main": [
                [target.model_dump() for target in port]
                for port in entry.main
            ]
        }
    return result


def _build_assembler_prompt(planned_edges: list[dict], node_list: list[dict]) -> str:
    """Assemble the human message for the Assembler agent."""
    sections = [
        f"## Planned edges\n{json.dumps(planned_edges, indent=2)}",
        f"## Node list\n{json.dumps(node_list, indent=2)}",
    ]
    return "\n\n".join(sections)


_BRANCH_INDEX_MAP = {"true": 0, "1": 0, "false": 1, "2": 1, "3": 2}


def _build_connections_from_edges(planned_edges: list[dict]) -> dict:
    """Deterministically build n8n connections from planned edges.

    Handles linear chains and If/Switch branching using standard output indices.
    """
    connections: dict[str, dict] = {}
    for edge in planned_edges:
        source = edge.get("from_node", "")
        target = edge.get("to_node", "")
        branch = edge.get("branch")
        output_index = _BRANCH_INDEX_MAP.get(str(branch).lower(), 0) if branch else 0

        source_entry = connections.setdefault(source, {"main": []})
        main_list: list = source_entry["main"]
        # Pad with empty lists up to the required output index
        while len(main_list) <= output_index:
            main_list.append([])
        main_list[output_index].append({"node": target, "type": "main", "index": 0})

    return connections


def _extract_node_list(results: list[dict]) -> list[dict]:
    """Extract node name and type from build results for the agent prompt."""
    return [
        {"node_name": r["node_name"], "node_type": r["node_json"].get("type", "")}
        for r in results
    ]


# ── Pre-validation helpers ───────────────────────────────────────────────────

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


def _validate_connections(
    connections: dict,
    planned_edges: list[dict],
    node_list: list[dict],
) -> str | None:
    """Validate connections cover all planned edges. Returns error message or None."""
    if not planned_edges:
        return None

    if not connections and len(node_list) > 1:
        return f"Empty connections dict but {len(node_list)} nodes and {len(planned_edges)} planned edges"

    for edge in planned_edges:
        source = edge.get("from_node", "")
        target = edge.get("to_node", "")
        source_conns = connections.get(source, {}).get("main", [])
        found = False
        for output_port in source_conns:
            for conn in output_port:
                if conn.get("node") == target:
                    found = True
                    break
            if found:
                break
        if not found:
            return f"Missing connection: '{source}' → '{target}' (in planned_edges but not in connections)"

    return None


# ── Workflow assembly ────────────────────────────────────────────────────────

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


# ── Error output builders ───────────────────────────────────────────────────

async def _emit_and_return_error(bus: object, start: float, output: dict) -> dict:
    """Emit an error event and return the pre-built error output."""
    elapsed = int((time.monotonic() - start) * 1000)
    if bus:
        error_msg = output.get("error_message", "Unknown error")
        await bus.emit_complete("assemble", "Assembler", "error", error_msg, duration_ms=elapsed)
    return output


def _build_validation_failure_output(failed: list[dict]) -> dict:
    """Build the state patch that short-circuits to the debugger."""
    error_messages: list[str] = []
    for failed_result in failed:
        error_messages.extend(failed_result.get("validation_errors", []))

    first_node_name = failed[0].get("node_name", "unknown")
    summary = f"{len(failed)} node(s) failed validation: {'; '.join(error_messages[:3])}"

    logger.warning("[Assembler] Validation gate failed — %s", summary)
    return {
        "status": "failed",
        "error_message": summary,
        "messages": [HumanMessage(content=f"[Assembler] {len(failed)} node(s) failed validation ({first_node_name}): {summary}")],
    }


def _build_edge_error_output(error_message: str) -> dict:
    """Build the state patch for a dangling edge error."""
    logger.warning("[Assembler] Edge validation failed — %s", error_message)
    return {
        "status": "failed",
        "error_message": error_message,
        "messages": [HumanMessage(content=f"[Assembler] Edge validation failed: {error_message}")],
    }
