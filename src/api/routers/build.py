"""Phase 2 — Build router."""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline
from src.api.lifespan.pipeline import get_pipeline
from src.api.lifespan.redis import get_redis
from src.api.schemas import BuildRequest, BuildResponse, JobState
from src.services.pipeline import build

log = logging.getLogger("aria.api.build")
router = APIRouter(prefix="/build", tags=["Phase 2 — Build"])

_PING_INTERVAL = 15
_TERMINAL = {"done", "error"}


@router.post("", response_model=BuildResponse, status_code=202)
async def start_build(
    body: BuildRequest,
    redis: Redis = Depends(get_redis),
    pipeline: ARIAPipeline = Depends(get_pipeline),
) -> BuildResponse:
    try:
        await build.validate_preflight(body.preflight_id, redis)
    except ValueError as exc:
        status = 404 if "not found" in str(exc) else 409
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    job_id = str(uuid4())
    log.info("POST /build | job_id=%s | preflight_id=%s", job_id, body.preflight_id)
    initial = JobState(job_id=job_id, status="building")
    await redis.set(f"job:{job_id}", initial.model_dump_json(), ex=86_400)
    asyncio.create_task(build.run_build(job_id, body.preflight_id, redis, pipeline))
    log.info("Build background task created | job_id=%s", job_id)
    return BuildResponse(build_job_id=job_id, status="building")


@router.get("/{job_id}/stream")
async def stream_build(
    job_id: str,
    redis: Redis = Depends(get_redis),
) -> StreamingResponse:
    log.info("GET /build/%s/stream — SSE connection opened", job_id)
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="Build job not found")
    return StreamingResponse(
        _sse_generator(job_id, redis),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
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
