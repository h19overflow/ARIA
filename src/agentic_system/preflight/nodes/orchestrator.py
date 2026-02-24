"""Pre-Flight Orchestrator — parses user intent into required node types."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.base_agent import BaseAgent
from src.agentic_system.shared.state import ARIAState
from src.agentic_system.preflight.schemas.blueprint import OrchestratorOutput
from src.agentic_system.preflight.prompts.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT


_agent = BaseAgent[OrchestratorOutput](
    prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    schema=OrchestratorOutput,
    name="PreflightOrchestrator",
)


async def orchestrator_node(state: ARIAState) -> dict:
    """Parse user intent, extract required n8n node types."""
    intent = state["intent"]
    messages = [HumanMessage(content=intent)]

    result: OrchestratorOutput = await _agent.invoke(messages)

    # Ensure trigger node is included
    required = list(result.required_nodes)
    if result.trigger_node not in required:
        required.insert(0, result.trigger_node)

    return {
        "required_nodes": required,
        "status": "planning",
        "messages": [HumanMessage(content=f"[Orchestrator] Plan: {result.intent_summary}")],
    }
