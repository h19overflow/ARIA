"""Build Cycle Engineer — assembles workflow JSON from templates + blueprint."""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.build_cycle.schemas.workflow import EngineerOutput
from src.agentic_system.build_cycle.prompts.engineer import ENGINEER_SYSTEM_PROMPT


_agent = BaseAgent[EngineerOutput](
    prompt=ENGINEER_SYSTEM_PROMPT,
    schema=EngineerOutput,
    name="Engineer",
)


async def engineer_node(state: ARIAState) -> dict:
    """Use LLM to assemble a complete n8n workflow JSON."""
    blueprint = state["build_blueprint"]
    templates = state["node_templates"]
    cred_ids = state.get("resolved_credential_ids", {})

    prompt = _build_engineer_prompt(blueprint, templates, cred_ids)
    messages = [HumanMessage(content=prompt)]

    result: EngineerOutput = await _agent.invoke(messages)
    workflow_json = _to_n8n_payload(result, cred_ids)

    return {
        "workflow_json": workflow_json,
        "status": "building",
        "messages": [HumanMessage(
            content=f"[Engineer] Built workflow '{result.workflow_name}' with {len(result.nodes)} nodes."
        )],
    }


def _build_engineer_prompt(
    blueprint: dict, templates: list[dict], cred_ids: dict[str, str]
) -> str:
    """Build the human message content for the engineer."""
    return (
        f"Intent: {blueprint['intent']}\n"
        f"Required nodes: {blueprint['required_nodes']}\n"
        f"Credential IDs: {json.dumps(cred_ids)}\n"
        f"Node templates:\n{json.dumps(templates, indent=2)}"
    )


def _to_n8n_payload(output: EngineerOutput, cred_ids: dict[str, str]) -> dict:
    """Convert EngineerOutput to n8n POST /workflows body."""
    nodes = []
    for i, node in enumerate(output.nodes):
        n8n_node = {
            "name": node.name,
            "type": node.type,
            "parameters": node.parameters,
            "position": [250 * i, 300],
            "typeVersion": 1,
        }
        if node.credentials:
            n8n_node["credentials"] = node.credentials
        nodes.append(n8n_node)

    connections = _build_connections(output.connections)

    return {
        "name": output.workflow_name,
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
    }


def _build_connections(connections: list) -> dict:
    """Build n8n connections dict from WorkflowConnection list."""
    result: dict = {}
    for conn in connections:
        result.setdefault(conn.source, {"main": [[]]})
        result[conn.source]["main"][0].append({
            "node": conn.target,
            "type": "main",
            "index": conn.target_input,
        })
    return result
