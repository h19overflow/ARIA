"""Phase 1 — Preflight router (conversational agent pattern)."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from src.agentic_system.preflight.agent import PreflightAgent
from src.api.lifespan.preflight import get_preflight_agent
from src.api.lifespan.redis import get_redis
from src.api.schemas import (
    ErrorResponse,
    StartPreflightRequest,
    StartPreflightResponse,
    PreflightMessageRequest,
    PreflightStatusResponse,
)
from src.services.preflight.service import (
    initialize_preflight,
    process_preflight_message,
    get_preflight_status,
)

log = logging.getLogger("aria.api.preflight")

router = APIRouter(prefix="/preflight", tags=["Phase 1 — Preflight"])


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", request.headers.get("X-Request-ID", str(uuid.uuid4())))


@router.post(
    "/start",
    response_model=StartPreflightResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Start a preflight session",
    description="Reads Phase 0 conversation notes from Redis and initialises a new preflight session.",
)
async def start_preflight(
    body: StartPreflightRequest,
    response: Response,
    request: Request,
    redis: Redis = Depends(get_redis),
    agent: PreflightAgent = Depends(get_preflight_agent),
) -> StartPreflightResponse:
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id
    try:
        preflight_id = await initialize_preflight(body.conversation_id, redis, agent)
        return StartPreflightResponse(preflight_id=preflight_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        log.error("Failed to start preflight: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start preflight")


@router.post(
    "/{preflight_id}/message",
    response_class=StreamingResponse,
    summary="Send a message and stream the preflight agent response",
    description="Streams agent tokens and tool events as Server-Sent Events.",
)
async def send_preflight_message(
    preflight_id: str,
    payload: PreflightMessageRequest,
    response: Response,
    request: Request,
    agent: PreflightAgent = Depends(get_preflight_agent),
) -> StreamingResponse:
    request_id = _get_request_id(request)
    response.headers["X-Request-ID"] = request_id

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event in process_preflight_message(preflight_id, payload.message, agent):
                if await request.is_disconnected():
                    break
                data = json.dumps(event) if isinstance(event, dict) else str(event)
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error("Preflight stream error preflight_id=%s: %s", preflight_id, e, exc_info=True)
            error_event = {
                "type": "error",
                "error": {"code": "STREAM_ERROR", "message": str(e)},
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Request-ID": request_id},
    )


@router.get(
    "/{preflight_id}/status",
    summary="Get preflight session status",
    description="Returns committed state and current notes for a preflight session.",
)
async def get_status(preflight_id: str) -> dict:
    try:
        return await get_preflight_status(preflight_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
