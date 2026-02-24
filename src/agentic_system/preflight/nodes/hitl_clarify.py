"""Pre-Flight HITL Clarify — interrupts to ask user a clarifying question."""
from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from src.agentic_system.shared.state import ARIAState

MAX_ORCHESTRATOR_TURNS = 3


async def hitl_clarify_node(state: ARIAState) -> dict:
    """Interrupt to ask user a clarifying question, append answer to messages."""
    question = state.get("pending_question", "Could you clarify your request?")

    user_answer = interrupt({
        "type": "orchestrator_clarification",
        "question": question,
    })

    turns = state.get("orchestrator_turns", 0) + 1
    return {
        "orchestrator_turns": turns,
        "messages": [HumanMessage(content=user_answer)],
    }
