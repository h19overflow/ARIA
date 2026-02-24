"""Workflow submission router."""
from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from src.api.lifespan.redis import get_redis
from src.api.schemas import WorkflowRequest, WorkflowResponse, JobState
from src.services import pipeline_service

log = logging.getLogger("aria.api.workflows")
router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=202)
async def create_workflow(
    body: WorkflowRequest,
    redis: Redis = Depends(get_redis),
) -> WorkflowResponse:
    job_id = str(uuid4())
    log.info("POST /workflows | job_id=%s | description=%r", job_id, body.description[:80])
    initial = JobState(job_id=job_id, status="planning")
    await redis.set(f"job:{job_id}", initial.model_dump_json(), ex=86_400)
    asyncio.create_task(pipeline_service.run_job(job_id, body.description, redis))
    log.info("Background task created | job_id=%s", job_id)
    return WorkflowResponse(job_id=job_id, status="planning")
