"""Phase 2 — Build service.

Reads the BuildBlueprint from a committed preflight in Redis,
streams the build cycle LangGraph subgraph, and handles HITL interrupts.
"""
from __future__ import annotations

import logging
import traceback

from langgraph.errors import GraphInterrupt
from langgraph.types import Command
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline  # noqa: TC002
from src.agentic_system.preflight.state import PreflightState
from src.agentic_system.shared.state import ARIAState, BuildBlueprint, WorkflowTopology
from src.api.schemas import JobState, SSEEvent
from src.services.pipeline._sse_helpers import (
    apply_build_chunk, coerce_state, detect_interrupt,
    is_interrupt_chunk, publish, serialize, wait_resume, write_job,
)

log = logging.getLogger("aria.build")


async def validate_preflight(preflight_id: str, redis: Redis) -> None:
    """Raise ValueError if preflight is missing or not committed."""
    raw = await redis.get(f"preflight:{preflight_id}")
    if raw is None:
        raise ValueError(f"Preflight {preflight_id!r} not found")
    state = PreflightState.model_validate_json(raw)
    if not state.committed:
        raise ValueError("Preflight is not committed — complete Phase 1 first")


async def run_build(
    job_id: str, preflight_id: str, redis: Redis, pipeline: ARIAPipeline,
) -> None:
    """Background task. Reads BuildBlueprint from Redis, runs build cycle, handles HITL."""
    log.info("[%s] Build job started | preflight_id=%s", job_id, preflight_id)
    try:
        preflight_state = await _load_state_for_build(preflight_id, redis)
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


async def _load_state_for_build(preflight_id: str, redis: Redis) -> ARIAState:
    """Load committed PreflightState from Redis and convert to ARIAState."""
    raw = await redis.get(f"preflight:{preflight_id}")
    if raw is None:
        raise ValueError(f"Preflight {preflight_id!r} not found")
    state = PreflightState.model_validate_json(raw)
    if not state.committed:
        raise ValueError("Preflight is not committed — complete Phase 1 first")
    return _preflight_to_aria_state(state)


def _preflight_to_aria_state(state: PreflightState) -> ARIAState:
    """Convert PreflightState (new chat agent) to ARIAState for the build cycle."""
    notes = state.notes
    empty_topology: WorkflowTopology = {
        "nodes": [], "edges": [], "entry_node": "", "branch_nodes": [],
    }
    blueprint: BuildBlueprint = {
        "intent": notes.summary or "Build the requested workflow",
        "required_nodes": notes.required_nodes,
        "credential_ids": notes.resolved_credential_ids,
        "topology": empty_topology,
        "user_description": notes.summary,
    }
    return {
        "messages": [],
        "intent": notes.summary,
        "required_nodes": notes.required_nodes,
        "resolved_credential_ids": notes.resolved_credential_ids,
        "pending_credential_types": [],
        "credential_guide_payload": None,
        "build_blueprint": blueprint,
        "topology": empty_topology,
        "user_description": notes.summary,
        "intent_summary": notes.summary,
        "conversation_notes": None,
        "node_templates": [],
        "workflow_json": None,
        "n8n_workflow_id": None,
        "n8n_execution_id": None,
        "execution_result": None,
        "classified_error": None,
        "fix_attempts": 0,
        "webhook_url": None,
        "status": "planning",
        "build_phase": 0,
        "total_phases": 1,
        "phase_node_map": [],
        "paused_for_input": False,
    }


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
                if is_interrupt_chunk(chunk):
                    interrupted = True
                    break
                current_input = await apply_build_chunk(redis, job_id, chunk, coerce_state(current_input))
        except GraphInterrupt:
            interrupted = True  # safety fallback for older LangGraph

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
