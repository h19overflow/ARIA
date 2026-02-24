"""Build Cycle Debugger — classify error AND apply fix in a single LLM call.

Replaces the sequential error_classifier_node → fix_node pair, halving
LLM call count and latency on the critical recovery path.
"""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, ClassifiedError
from src.agentic_system.build_cycle.schemas.execution import DebuggerOutput
from src.agentic_system.build_cycle.prompts.debugger import DEBUGGER_SYSTEM_PROMPT


_agent = BaseAgent[DebuggerOutput](
    prompt=DEBUGGER_SYSTEM_PROMPT,
    schema=DebuggerOutput,
    name="Debugger",
)

_FIXABLE_TYPES = {"schema", "logic"}


async def debugger_node(state: ARIAState) -> dict:
    """Classify execution error and apply fix in one LLM call."""
    exec_result = state["execution_result"]
    workflow_json = state["workflow_json"]
    fix_attempts = state.get("fix_attempts", 0)
    error_data = exec_result.get("error") or {}

    prompt = (
        f"Attempt: {fix_attempts + 1}/3\n"
        f"Error:\n{json.dumps(error_data, indent=2)}\n\n"
        f"Workflow:\n{json.dumps(workflow_json, indent=2)}"
    )
    result: DebuggerOutput = await _agent.invoke([HumanMessage(content=prompt)])

    classified: ClassifiedError = {
        "type": result.error_type,
        "node_name": result.node_name,
        "message": result.message,
        "description": result.description,
        "line_number": result.line_number,
        "stack": error_data.get("stack"),
    }

    updates: dict = {
        "classified_error": classified,
        "fix_attempts": fix_attempts + 1,
        "messages": [HumanMessage(
            content=f"[Debugger] {result.error_type} in '{result.node_name}': {result.message}"
        )],
    }

    if result.error_type in _FIXABLE_TYPES and result.fixed_parameters is not None:
        updates["workflow_json"] = _apply_fix(workflow_json, result)
        updates["status"] = "building"
        updates["messages"].append(HumanMessage(
            content=f"[Debugger] Fix applied to '{result.node_name}': {result.explanation}"
        ))

    return updates


def _apply_fix(workflow_json: dict, result: DebuggerOutput) -> dict:
    """Patch the target node's parameters in place."""
    patched = dict(workflow_json)
    nodes = list(patched.get("nodes", []))
    for i, node in enumerate(nodes):
        if node["name"] == result.node_name:
            nodes[i] = {**node, "parameters": result.fixed_parameters}
            break
    patched["nodes"] = nodes
    return patched
