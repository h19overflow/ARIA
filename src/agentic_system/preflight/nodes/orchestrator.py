"""Pre-Flight Orchestrator — parses user intent with optional clarification rounds."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState, WorkflowTopology
from src.agentic_system.preflight.schemas.orchestrator_decision import OrchestratorDecision
from src.agentic_system.preflight.schemas.blueprint import OrchestratorOutput
from src.agentic_system.preflight.prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT
from src.agentic_system.preflight.tools import ORCHESTRATOR_TOOLS


_agent = BaseAgent[OrchestratorDecision](
    prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    schema=OrchestratorDecision,
    tools=ORCHESTRATOR_TOOLS,
    name="PreflightOrchestrator",
)


async def orchestrator_node(state: ARIAState) -> dict:
    """Parse user intent, decide whether to clarify or commit."""
    messages = list(state.get("messages", []))
    if not messages:
        messages = [HumanMessage(content=state["intent"])]

    result: OrchestratorDecision = await _agent.invoke(messages)

    if result.decision == "clarify" and result.clarification:
        return _handle_clarify(result)
    return _handle_commit(result)


def _handle_clarify(result: OrchestratorDecision) -> dict:
    """Return clarification request to state for HITL node."""
    question = result.clarification.question
    return {
        "orchestrator_decision": "clarify",
        "pending_question": question,
        "messages": [HumanMessage(
            content=f"[Orchestrator] Clarifying: {question}",
        )],
    }


def _extract_topology(output: OrchestratorOutput) -> WorkflowTopology:
    """Pull topology from OrchestratorOutput; default to linear chain if missing."""
    if output.topology:
        return output.topology
    nodes = list(output.required_nodes)
    if output.trigger_node not in nodes:
        nodes.insert(0, output.trigger_node)
    edges = [
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


def _handle_commit(result: OrchestratorDecision) -> dict:
    """Extract final plan from OrchestratorDecision and commit."""
    output = result.output
    if not output:
        return {
            "orchestrator_decision": "commit",
            "required_nodes": ["webhook"],
            "status": "planning",
            "messages": [HumanMessage(content="[Orchestrator] Committed with default plan.")],
        }

    fields = _extract_blueprint_fields(output)
    return {
        "orchestrator_decision": "commit",
        "intent_summary": output.intent_summary,
        **fields,
        "messages": [HumanMessage(content=f"[Orchestrator] Plan: {output.intent_summary}")],
    }
