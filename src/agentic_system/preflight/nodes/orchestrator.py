"""Pre-Flight Orchestrator — parses ConversationNotes into a BuildBlueprint."""
from __future__ import annotations

import json
from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, WorkflowTopology, WorkflowEdge
from src.agentic_system.shared.errors import ExtractionError
from src.agentic_system.preflight.schemas.blueprint import OrchestratorOutput
from src.agentic_system.preflight.prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from src.agentic_system.preflight.tools.rag_tools import search_n8n_nodes

# Only give the orchestrator the RAG search tool — credential lookup is
# handled downstream by the Credential Scanner, so exposing it here just
# wastes tool-call rounds.
_ORCHESTRATOR_TOOLS_SLIM = [search_n8n_nodes]

_agent = BaseAgent[OrchestratorOutput](
    prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    schema=OrchestratorOutput,
    tools=_ORCHESTRATOR_TOOLS_SLIM,
    name="PreflightOrchestrator",
    model_name="gemini-3-flash-preview",
    temperature=0.2,
    recursion_limit=10,
)


async def orchestrator_node(state: ARIAState) -> dict:
    """Parse ConversationNotes into OrchestratorOutput."""
    notes = state.get("conversation_notes")
    if not notes:
        # Fallback if no notes provided
        notes = {"summary": state.get("intent", "Unknown intent")}

    # Convert notes to a formatted string for the LLM
    notes_str = json.dumps(notes, indent=2)
    messages = [HumanMessage(content=f"Here are the ConversationNotes:\n{notes_str}")]

    try:
        output: OrchestratorOutput = await _agent.invoke(messages)
    except Exception as e:
        # If the LLM fails to map to the schema (e.g., invalid n8n nodes)
        raise ExtractionError(
            f"Failed to extract blueprint from notes: {str(e)}",
            agent="PreflightOrchestrator"
        ) from e

    if output.extraction_error:
        raise ExtractionError(
            output.extraction_error,
            agent="PreflightOrchestrator"
        )

    fields = _extract_blueprint_fields(output)
    return {
        "intent_summary": output.intent_summary,
        **fields,
        "messages": [HumanMessage(content=f"[Orchestrator] Extracted Plan: {output.intent_summary}")],
    }


def _extract_topology(output: OrchestratorOutput) -> WorkflowTopology:
    """Pull topology from OrchestratorOutput; default to linear chain if missing."""
    if output.topology:
        return output.topology
    nodes = list(output.required_nodes)
    if output.trigger_node not in nodes:
        nodes.insert(0, output.trigger_node)
    edges: list[WorkflowEdge] = [
        {"from_node": nodes[i], "to_node": nodes[i + 1], "branch": None}
        for i in range(len(nodes) - 1)
    ]
    return {
        "nodes": nodes,
        "edges": edges,
        "entry_node": nodes[0] if nodes else output.trigger_node,
        "branch_nodes": [],
    }


def _extract_blueprint_fields(output: OrchestratorOutput) -> dict:
    """Return state fields: required_nodes, topology, user_description, status."""
    required = list(output.required_nodes)
    if output.trigger_node not in required:
        required.insert(0, output.trigger_node)
    return {
        "required_nodes": required,
        "topology": _extract_topology(output),
        "user_description": output.user_description,
        "status": "planning",
    }
