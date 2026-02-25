"""Workflow submission router."""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline
from src.api.lifespan.pipeline import get_pipeline
from src.api.lifespan.redis import get_redis
from src.api.schemas import WorkflowRequest, WorkflowResponse, JobState
from src.services import pipeline_service

log = logging.getLogger("aria.api.workflows")
router = APIRouter(prefix="/workflows", tags=["workflows"])


async def _resolve_description(body: WorkflowRequest, redis: Redis) -> str:
    """Return description from body, or fall back to conversation summary in Redis."""
    if body.description:
        return body.description

    if body.conversation_id:
        raw = await redis.get(f"conversation:{body.conversation_id}")
        if raw:
            try:
                data = json.loads(raw)
                summary = data.get("notes", {}).get("summary", "")
                if summary:
                    return summary
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


@router.post("", response_model=WorkflowResponse, status_code=202)
async def create_workflow(
    body: WorkflowRequest,
    redis: Redis = Depends(get_redis),
    pipeline: ARIAPipeline = Depends(get_pipeline),
) -> WorkflowResponse:
    description = await _resolve_description(body, redis)
    job_id = str(uuid4())
    log.info("POST /workflows | job_id=%s | description=%r", job_id, description[:80])
    initial = JobState(job_id=job_id, status="planning")
    await redis.set(f"job:{job_id}", initial.model_dump_json(), ex=86_400)
    asyncio.create_task(pipeline_service.run_job(job_id, description, redis, pipeline))
    log.info("Background task created | job_id=%s", job_id)
    return WorkflowResponse(job_id=job_id, status="planning")
