"""Jobs status, SSE stream, and resume router."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from src.api.lifespan.redis import get_redis
from src.api.schemas import JobState, JobStatusResponse, ResumeRequest

log = logging.getLogger("aria.api.jobs")
router = APIRouter(prefix="/jobs", tags=["jobs"])

_PING_INTERVAL = 15
_TERMINAL = {"done", "error"}


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, redis: Redis = Depends(get_redis)) -> JobStatusResponse:
    log.debug("GET /jobs/%s", job_id)
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
        log.warning("GET /jobs/%s → 404 not found", job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    job = JobState.model_validate_json(raw)
    log.debug("GET /jobs/%s → status=%s", job_id, job.status)
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        result=job.aria_state,
        error=job.error,
    )


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, redis: Redis = Depends(get_redis)) -> StreamingResponse:
    log.info("GET /jobs/%s/stream — SSE connection opened", job_id)
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
        log.warning("GET /jobs/%s/stream → 404 not found", job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    return StreamingResponse(
        _sse_generator(job_id, redis),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _sse_generator(job_id: str, redis: Redis) -> AsyncGenerator[str, None]:
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


@router.post("/{job_id}/resume", status_code=204)
async def resume_job(
    job_id: str,
    body: ResumeRequest,
    redis: Redis = Depends(get_redis),
) -> None:
    log.info("POST /jobs/%s/resume | action=%s", job_id, body.action)
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
        log.warning("POST /jobs/%s/resume → 404 not found", job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    job = JobState.model_validate_json(raw)
    if job.status != "interrupted":
        log.warning("POST /jobs/%s/resume → 409 not interrupted (status=%s)", job_id, job.status)
        raise HTTPException(status_code=409, detail=f"Job is not interrupted (status: {job.status})")
    payload = json.dumps(body.model_dump(exclude_none=True))
    await redis.publish(f"resume:{job_id}", payload)
    log.info("Resume published | job=%s payload=%s", job_id, payload)
