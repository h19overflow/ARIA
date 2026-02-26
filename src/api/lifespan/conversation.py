from fastapi import Request

from src.services.conversation.service import ConversationService

_service: ConversationService | None = None


async def startup() -> None:
    global _service
    _service = ConversationService()


async def shutdown() -> None:
    global _service
    _service = None


def get_conversation_service(request: Request) -> ConversationService:  # noqa: ARG001
    if _service is None:
        raise RuntimeError("ConversationService not initialised — lifespan not running")
    return _service
