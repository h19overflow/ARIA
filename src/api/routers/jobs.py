"""Jobs status and resume router."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis

from src.api.lifespan.redis import get_redis
from src.api.schemas import JobState, JobStatusResponse, ResumeRequest

log = logging.getLogger("aria.api.jobs")
router = APIRouter(prefix="/jobs", tags=["jobs"])


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
