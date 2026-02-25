from fastapi import Request

from src.agentic_system.conversation.agent import ConversationAgent

_agent: ConversationAgent | None = None


async def startup() -> None:
    global _agent
    _agent = ConversationAgent()


async def shutdown() -> None:
    global _agent
    _agent = None


def get_conversation_agent(request: Request) -> ConversationAgent:  # noqa: ARG001
    if _agent is None:
        raise RuntimeError("ConversationAgent not initialised — lifespan not running")
    return _agent
