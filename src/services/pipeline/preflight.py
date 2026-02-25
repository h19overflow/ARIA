"""Phase 1 — Preflight service.

Streams the preflight LangGraph subgraph, handles HITL interrupts,
and writes the final BuildBlueprint into Redis when done.
"""
from __future__ import annotations

import logging
import traceback

from langgraph.errors import GraphInterrupt
from langgraph.types import Command
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline  # noqa: TC002
from src.agentic_system.shared.state import ARIAState
from src.api.schemas import JobState, SSEEvent
from src.services.pipeline._sse_helpers import (
    apply_chunk, build_initial_state, coerce_state,
    detect_interrupt, publish, serialize, wait_resume, write_job,
)

log = logging.getLogger("aria.preflight")


async def run_preflight(
    job_id: str, description: str, redis: Redis, pipeline: ARIAPipeline,
    conversation_notes: dict | None = None,
) -> None:
    """Background task. Streams preflight graph, handles HITL, writes job:{id}."""
    config = {"configurable": {"thread_id": job_id}}
    initial_state = build_initial_state(description, conversation_notes)
    log.info("[%s] Preflight job started | description=%r", job_id, description[:80])
    try:
        await write_job(redis, job_id, JobState(job_id=job_id, status="planning"))
        final = await _stream_preflight(job_id, initial_state, config, redis, pipeline)
        log.info("[%s] Preflight complete | build_blueprint=%s", job_id, bool(final.get("build_blueprint")))
        await publish(redis, job_id, SSEEvent(type="done", aria_state=serialize(final)))
        await write_job(redis, job_id, JobState(job_id=job_id, status="done", aria_state=serialize(final)))
    except Exception as exc:
        tb = traceback.format_exc()
        log.error("[%s] Preflight failed: %s\n%s", job_id, exc, tb)
        await publish(redis, job_id, SSEEvent(type="error", message=str(exc)))
        await write_job(redis, job_id, JobState(job_id=job_id, status="failed", error=tb))


async def _stream_preflight(
    job_id: str, state: ARIAState, config: dict, redis: Redis, pipeline: ARIAPipeline,
) -> ARIAState:
    """Stream preflight graph, resuming through HITL interrupts until END."""
    log.info("[%s] Preflight streaming starting", job_id)
    current_input: ARIAState | Command = state  # type: ignore[type-arg]

    while True:
        interrupted = False
        try:
            async for chunk in pipeline._preflight.astream(current_input, config=config):
                current_input = await apply_chunk(redis, job_id, chunk, coerce_state(current_input), "preflight")
        except GraphInterrupt:
            interrupted = True

        if interrupted:
            snapshot = await pipeline._preflight.aget_state(config)
            snap_state: ARIAState = snapshot.values  # type: ignore[assignment]
            kind, payload = detect_interrupt(snap_state)
            log.info("[%s] Preflight interrupted | kind=%s | question=%r", job_id, kind, payload.get("question", ""))
            await publish(redis, job_id, SSEEvent(type="interrupt", kind=kind, payload=payload))
            await write_job(redis, job_id, JobState(
                job_id=job_id, status="interrupted", aria_state=serialize(snap_state),
            ))
            resume_value = await wait_resume(redis, job_id)
            log.info("[%s] Resume received | value=%r", job_id, str(resume_value)[:80])
            current_input = Command(resume=resume_value)
        else:
            snapshot = await pipeline._preflight.aget_state(config)
            final: ARIAState = snapshot.values  # type: ignore[assignment]
            log.info("[%s] Preflight ended | build_blueprint=%s | topology_nodes=%s",
                     job_id, bool(final.get("build_blueprint")),
                     len((final.get("topology") or {}).get("nodes", [])))
            return final
