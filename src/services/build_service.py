"""Phase 2 — Build service.

Reads the BuildBlueprint from a completed preflight job in Redis,
streams the build cycle LangGraph subgraph, and handles HITL interrupts.
"""
from __future__ import annotations

import logging
import traceback

from fastapi import HTTPException
from langgraph.errors import GraphInterrupt
from langgraph.types import Command
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline  # noqa: TC002
from src.agentic_system.shared.state import ARIAState
from src.api.schemas import JobState, SSEEvent
from src.services._sse_helpers import (
    apply_build_chunk, coerce_state, detect_interrupt,
    publish, serialize, wait_resume, write_job,
)

log = logging.getLogger("aria.build")


async def load_preflight_state(preflight_job_id: str, redis: Redis) -> ARIAState:
    """Load and validate a completed preflight job from Redis."""
    raw = await redis.get(f"job:{preflight_job_id}")
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Preflight job {preflight_job_id!r} not found")
    job = JobState.model_validate_json(raw)
    if job.status != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Preflight job is not done (status: {job.status}). Complete Phase 1 first.",
        )
    if not job.aria_state:
        raise HTTPException(status_code=422, detail="Preflight job has no aria_state")
    return job.aria_state  # type: ignore[return-value]


async def run_build(
    job_id: str, preflight_job_id: str, redis: Redis, pipeline: ARIAPipeline,
) -> None:
    """Background task. Reads BuildBlueprint from Redis, runs build cycle, handles HITL."""
    log.info("[%s] Build job started | preflight_job_id=%s", job_id, preflight_job_id)
    try:
        preflight_state = await _load_state_for_build(preflight_job_id, redis)
        config = {"configurable": {"thread_id": job_id}}
        await write_job(redis, job_id, JobState(job_id=job_id, status="building"))
        final = await _stream_build(job_id, preflight_state, config, redis, pipeline)
        log.info("[%s] Build complete | status=%s", job_id, final.get("status"))
        await publish(redis, job_id, SSEEvent(type="done", aria_state=serialize(final)))
        await write_job(redis, job_id, JobState(job_id=job_id, status="done", aria_state=serialize(final)))
    except Exception as exc:
        tb = traceback.format_exc()
        log.error("[%s] Build failed: %s\n%s", job_id, exc, tb)
        await publish(redis, job_id, SSEEvent(type="error", message=str(exc)))
        await write_job(redis, job_id, JobState(job_id=job_id, status="failed", error=tb))


async def _load_state_for_build(preflight_job_id: str, redis: Redis) -> ARIAState:
    """Load preflight state from Redis for use as build input."""
    raw = await redis.get(f"job:{preflight_job_id}")
    if raw is None:
        raise ValueError(f"Preflight job {preflight_job_id!r} not found in Redis")
    job = JobState.model_validate_json(raw)
    if job.status != "done":
        raise ValueError(f"Preflight job is not done (status: {job.status})")
    if not job.aria_state:
        raise ValueError("Preflight job has no aria_state")
    return job.aria_state  # type: ignore[return-value]


async def _stream_build(
    job_id: str, state: ARIAState, config: dict, redis: Redis, pipeline: ARIAPipeline,
) -> ARIAState:
    """Stream build cycle graph, resuming through HITL escalation interrupts."""
    log.info("[%s] Build cycle streaming | blueprint_intent=%r",
             job_id, (state.get("build_blueprint") or {}).get("intent", "")[:60])
    current_input: ARIAState | Command = state  # type: ignore[type-arg]

    while True:
        interrupted = False
        try:
            async for chunk in pipeline._build_cycle.astream(current_input, config=config):
                current_input = await apply_build_chunk(redis, job_id, chunk, coerce_state(current_input))
        except GraphInterrupt:
            interrupted = True

        if interrupted:
            snapshot = await pipeline._build_cycle.aget_state(config)
            snap_state: ARIAState = snapshot.values  # type: ignore[assignment]
            kind, payload = detect_interrupt(snap_state)
            log.info("[%s] Build interrupted | kind=%s", job_id, kind)
            await publish(redis, job_id, SSEEvent(type="interrupt", kind=kind, payload=payload))
            await write_job(redis, job_id, JobState(
                job_id=job_id, status="interrupted", aria_state=serialize(snap_state),
            ))
            resume_value = await wait_resume(redis, job_id)
            log.info("[%s] Build resume received | value=%r", job_id, str(resume_value)[:80])
            current_input = Command(resume=resume_value)
        else:
            snapshot = await pipeline._build_cycle.aget_state(config)
            final: ARIAState = snapshot.values  # type: ignore[assignment]
            log.info("[%s] Build cycle ended | status=%s", job_id, final.get("status"))
            return final
