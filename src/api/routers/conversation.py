import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.responses import StreamingResponse

from src.api.lifespan.conversation import get_conversation_service
from src.services.conversation.service import ConversationService
from src.api.schemas import StartConversationResponse, MessageRequest, ErrorResponse

router = APIRouter(
    prefix="/conversation",
    tags=["Conversation Phase 0"]
)

# --- Dependencies ---

async def get_current_user(request: Request) -> dict:
    """Dependency to get the current authenticated user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return {"user_id": "anonymous"}
    return {"user_id": "authenticated_user"}

def get_request_id(request: Request) -> str:
    """Extract correlation ID from request state or headers."""
    return getattr(request.state, "request_id", request.headers.get("X-Request-ID", str(uuid.uuid4())))

# --- Endpoints ---

@router.post(
    "/start",
    response_model=StartConversationResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Start a new conversation",
    description="Initializes the Redis state for a new Phase 0 conversation and returns a unique conversation ID."
)
async def start_conversation(
    response: Response,
    request: Request,
    service: ConversationService = Depends(get_conversation_service),
    user: dict = Depends(get_current_user),
    request_id: str = Depends(get_request_id)
):
    response.headers["X-Request-ID"] = request_id
    try:
        conversation_id = await service.start_conversation()
        return StartConversationResponse(conversation_id=conversation_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": "Failed to start conversation", "details": {"error": str(e)}}}
        )

@router.post(
    "/{conversation_id}/message",
    response_class=StreamingResponse,
    summary="Send a message and stream the conversation response",
    description="Handles user input and streams the agent logic response as Server-Sent Events (SSE)."
)
async def send_message_stream(
    conversation_id: str,
    payload: MessageRequest,
    response: Response,
    request: Request,
    service: ConversationService = Depends(get_conversation_service),
    user: dict = Depends(get_current_user),
    request_id: str = Depends(get_request_id)
):
    response.headers["X-Request-ID"] = request_id
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Process the message and consume the AsyncGenerator from the agent
            async for event in service.process_message(conversation_id, payload.message):
                if await request.is_disconnected():
                    break
                
                # Format as Server-Sent Event
                data = json.dumps(event) if isinstance(event, dict) else str(event)
                yield f"data: {data}\n\n"
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            error_event = {
                "type": "error",
                "error": {
                    "code": "STREAM_ERROR",
                    "message": "An error occurred during streaming",
                    "details": {"error": str(e)}
                }
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id
        }
    )
