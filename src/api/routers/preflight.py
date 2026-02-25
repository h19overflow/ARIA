"""Phase 1 — Preflight router."""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline
from src.api.lifespan.pipeline import get_pipeline
from src.api.lifespan.redis import get_redis
from src.api.schemas import JobState, PreflightRequest, PreflightResponse
from src.services import preflight_service

log = logging.getLogger("aria.api.preflight")
router = APIRouter(prefix="/preflight", tags=["Phase 1 — Preflight"])

_PING_INTERVAL = 15
_TERMINAL = {"done", "error"}


@router.post("", response_model=PreflightResponse, status_code=202)
async def start_preflight(
    body: PreflightRequest,
    redis: Redis = Depends(get_redis),
    pipeline: ARIAPipeline = Depends(get_pipeline),
) -> PreflightResponse:
    description, conversation_notes = await _resolve_description(body, redis)
    job_id = str(uuid4())
    log.info("POST /preflight | job_id=%s | description=%r", job_id, description[:80])
    initial = JobState(job_id=job_id, status="planning")
    await redis.set(f"job:{job_id}", initial.model_dump_json(), ex=86_400)
    asyncio.create_task(preflight_service.run_preflight(job_id, description, redis, pipeline, conversation_notes))
    log.info("Preflight background task created | job_id=%s", job_id)
    return PreflightResponse(preflight_job_id=job_id, status="planning")


@router.get("/{job_id}/stream")
async def stream_preflight(
    job_id: str,
    redis: Redis = Depends(get_redis),
) -> StreamingResponse:
    log.info("GET /preflight/%s/stream — SSE connection opened", job_id)
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="Preflight job not found")
    return StreamingResponse(
        _sse_generator(job_id, redis),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _resolve_description(body: PreflightRequest, redis: Redis) -> tuple[str, dict | None]:
    if body.description:
        return body.description, None
    if body.conversation_id:
        raw = await redis.get(f"conversation:{body.conversation_id}")
        if raw:
            try:
                data = json.loads(raw)
                notes = data.get("notes", {})
                summary = notes.get("summary", "")
                if summary:
                    return summary, notes
            except (json.JSONDecodeError, AttributeError):
                pass
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conversation has no committed summary yet. Complete Phase 0 first.",
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Either 'description' or 'conversation_id' must be provided.",
    )


async def _sse_generator(job_id: str, redis: Redis):
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"sse:{job_id}")
    try:
        while True:
            msg = await _poll_message(pubsub)
            if msg is None:
                yield ": ping\n\n"
                continue
            data = msg["data"]
            event_type = _event_type(data)
            log.debug("SSE event | job=%s type=%s", job_id, event_type)
            yield f"data: {data}\n\n"
            if event_type in _TERMINAL:
                log.info("SSE stream terminal | job=%s type=%s", job_id, event_type)
                break
    except GeneratorExit:
        log.info("SSE stream closed by client | job=%s", job_id)
    finally:
        await pubsub.unsubscribe(f"sse:{job_id}")


async def _poll_message(pubsub: object) -> dict | None:
    try:
        return await asyncio.wait_for(
            pubsub.get_message(ignore_subscribe_messages=True),  # type: ignore[union-attr]
            timeout=_PING_INTERVAL,
        )
    except asyncio.TimeoutError:
        return None


def _event_type(data: str | bytes) -> str:
    try:
        return json.loads(data).get("type", "unknown")
    except (json.JSONDecodeError, AttributeError):
        return "unknown"
