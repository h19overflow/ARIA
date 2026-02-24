"""Build Cycle Fix Agent — patches the failing node in the workflow."""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.schemas.workflow import FixOutput
from src.agentic_system.build_cycle.prompts.fix import FIX_SYSTEM_PROMPT


_agent = BaseAgent[FixOutput](
    prompt=FIX_SYSTEM_PROMPT,
    schema=FixOutput,
    name="FixAgent",
)


async def fix_node(state: ARIAState) -> dict:
    """Patch the failing node based on classified error."""
    workflow_json = state["workflow_json"]
    error = state["classified_error"]
    fix_attempts = state.get("fix_attempts", 0)

    prompt = (
        f"Error: {json.dumps(error, indent=2)}\n"
        f"Attempt: {fix_attempts + 1}/3\n"
        f"Workflow:\n{json.dumps(workflow_json, indent=2)}"
    )
    messages = [HumanMessage(content=prompt)]

    result: FixOutput = await _agent.invoke(messages)
    patched = _apply_fix(workflow_json, result)

    return {
        "workflow_json": patched,
        "fix_attempts": fix_attempts + 1,
        "status": "building",
        "messages": [HumanMessage(
            content=f"[Fix] Patched '{result.node_name}': {result.explanation}"
        )],
    }


def _apply_fix(workflow_json: dict, fix: FixOutput) -> dict:
    """Apply fix to the specific node in workflow JSON."""
    patched = dict(workflow_json)
    nodes = list(patched.get("nodes", []))
    for i, node in enumerate(nodes):
        if node["name"] == fix.node_name:
            nodes[i] = {**node, "parameters": fix.fixed_parameters}
            break
    patched["nodes"] = nodes
    return patched
