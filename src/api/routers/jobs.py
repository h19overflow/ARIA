"""Jobs status, SSE stream, and resume router."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from src.api.lifespan.redis import get_redis
from src.api.schemas import JobState, JobStatusResponse, ResumeRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])

_PING_INTERVAL = 15
_TERMINAL = {"done", "error"}


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str, redis: Redis = Depends(get_redis)) -> JobStatusResponse:
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JobState.model_validate_json(raw)
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        result=job.aria_state,
        error=job.error,
    )


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, redis: Redis = Depends(get_redis)) -> StreamingResponse:
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
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
            yield f"data: {data}\n\n"
            if _is_terminal(data):
                break
    except GeneratorExit:
        pass
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


def _is_terminal(data: str | bytes) -> bool:
    try:
        return json.loads(data).get("type") in _TERMINAL
    except (json.JSONDecodeError, AttributeError):
        return False


@router.post("/{job_id}/resume", status_code=204)
async def resume_job(
    job_id: str,
    body: ResumeRequest,
    redis: Redis = Depends(get_redis),
) -> None:
    raw = await redis.get(f"job:{job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JobState.model_validate_json(raw)
    if job.status != "interrupted":
        raise HTTPException(status_code=409, detail=f"Job is not interrupted (status: {job.status})")
    await redis.publish(f"resume:{job_id}", json.dumps(body.model_dump(exclude_none=True)))
