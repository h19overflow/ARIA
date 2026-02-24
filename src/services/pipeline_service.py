from __future__ import annotations

import json
import logging
import traceback

from langgraph.errors import GraphInterrupt
from langgraph.types import Command
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline
from src.agentic_system.shared.state import ARIAState
from src.api.schemas import JobState, SSEEvent

log = logging.getLogger("aria.pipeline")

_pipeline = ARIAPipeline()
_JOB_TTL = 86_400  # 24 hours


async def run_job(job_id: str, description: str, redis: Redis) -> None:
    """Entry point — called as asyncio.create_task from the workflows router."""
    config = {"configurable": {"thread_id": job_id}}
    initial_state = _build_initial_state(description)
    log.info("[%s] Job started | description=%r", job_id, description[:80])
    try:
        await _write_job(redis, job_id, JobState(job_id=job_id, status="planning"))
        state = await _stream_preflight(job_id, initial_state, config, redis)
        log.info("[%s] Preflight complete | build_blueprint=%s", job_id, bool(state.get("build_blueprint")))
        state = await _stream_build(job_id, state, config, redis)
        log.info("[%s] Build complete | status=%s", job_id, state.get("status"))
        await _publish(redis, job_id, SSEEvent(type="done", aria_state=_serialize(state)))
        await _write_job(redis, job_id, JobState(job_id=job_id, status="done", aria_state=_serialize(state)))
    except Exception as exc:
        tb = traceback.format_exc()
        log.error("[%s] Job failed: %s\n%s", job_id, exc, tb)
        await _publish(redis, job_id, SSEEvent(type="error", message=str(exc)))
        await _write_job(redis, job_id, JobState(job_id=job_id, status="failed", error=tb))


def _build_initial_state(description: str) -> ARIAState:
    return {  # type: ignore[return-value]
        "messages": [{"type": "human", "content": description}],
        "status": "planning", "intent": "", "required_nodes": [],
        "resolved_credential_ids": {}, "pending_credential_types": [],
        "credential_guide_payload": None, "build_blueprint": None, "topology": None,
        "user_description": description, "intent_summary": "",
        "orchestrator_decision": "", "pending_question": "", "orchestrator_turns": 0,
        "node_templates": [], "workflow_json": None, "n8n_workflow_id": None,
        "n8n_execution_id": None, "execution_result": None, "classified_error": None,
        "fix_attempts": 0, "webhook_url": None, "build_phase": 0,
        "total_phases": 1, "phase_node_map": [], "paused_for_input": False,
    }


async def _stream_preflight(job_id: str, state: ARIAState, config: dict, redis: Redis) -> ARIAState:
    """Stream preflight graph, resuming through HITL interrupts until END."""
    log.info("[%s] Preflight starting", job_id)
    current_input: ARIAState | Command = state  # type: ignore[type-arg]

    while True:
        interrupted = False
        try:
            async for chunk in _pipeline._preflight.astream(current_input, config=config):
                current_input = await _apply_chunk(redis, job_id, chunk, _coerce_state(current_input), "preflight")
        except GraphInterrupt:
            interrupted = True

        if interrupted:
            snapshot = await _pipeline._preflight.aget_state(config)
            snap_state: ARIAState = snapshot.values  # type: ignore[assignment]
            kind, payload = _detect_interrupt(snap_state)
            log.info("[%s] Preflight interrupted | kind=%s | question=%r", job_id, kind, payload.get("question", ""))
            await _publish(redis, job_id, SSEEvent(type="interrupt", kind=kind, payload=payload))
            await _write_job(redis, job_id, JobState(
                job_id=job_id, status="interrupted", aria_state=_serialize(snap_state),
            ))
            resume_value = await _wait_resume(redis, job_id)
            log.info("[%s] Resume received | value=%r", job_id, str(resume_value)[:80])
            current_input = Command(resume=resume_value)
        else:
            # Graph ran to END — pull final state from checkpointer
            snapshot = await _pipeline._preflight.aget_state(config)
            final: ARIAState = snapshot.values  # type: ignore[assignment]
            log.info("[%s] Preflight ended | build_blueprint=%s | topology_nodes=%s",
                     job_id, bool(final.get("build_blueprint")),
                     len((final.get("topology") or {}).get("nodes", [])))
            return final


def _coerce_state(inp: ARIAState | Command) -> ARIAState:  # type: ignore[type-arg]
    """Return inp as ARIAState — Commands don't have state fields."""
    if isinstance(inp, dict):
        return inp  # type: ignore[return-value]
    return {}  # type: ignore[return-value]


async def _apply_chunk(
    redis: Redis, job_id: str, chunk: dict, current_state: ARIAState, stage: str,
) -> ARIAState:
    """Merge a streaming chunk into state and publish node SSE events."""
    for node_name, update in chunk.items():
        if not isinstance(update, dict):
            log.debug("[%s] Skipping non-dict chunk from node=%s type=%s", job_id, node_name, type(update).__name__)
            continue
        current_state = {**current_state, **update}  # type: ignore[assignment]
        log.debug("[%s] Node completed | stage=%s node=%s", job_id, stage, node_name)
        await _publish(redis, job_id, SSEEvent(
            type="node", stage=stage, node_name=node_name, status="running",
            message=f"{node_name} completed",
            aria_state=_serialize(current_state),
        ))
        await _write_job(redis, job_id, JobState(
            job_id=job_id, status="planning", aria_state=_serialize(current_state),
        ))
    return current_state


async def _stream_build(job_id: str, state: ARIAState, config: dict, redis: Redis) -> ARIAState:
    """Stream build cycle graph, resuming through HITL escalation interrupts."""
    log.info("[%s] Build cycle starting | blueprint_intent=%r",
             job_id, (state.get("build_blueprint") or {}).get("intent", "")[:60])
    current_input: ARIAState | Command = state  # type: ignore[type-arg]

    while True:
        interrupted = False
        try:
            async for chunk in _pipeline._build_cycle.astream(current_input, config=config):
                current_input = await _apply_build_chunk(redis, job_id, chunk, _coerce_state(current_input))
        except GraphInterrupt:
            interrupted = True

        if interrupted:
            snapshot = await _pipeline._build_cycle.aget_state(config)
            snap_state: ARIAState = snapshot.values  # type: ignore[assignment]
            kind, payload = _detect_interrupt(snap_state)
            log.info("[%s] Build interrupted | kind=%s", job_id, kind)
            await _publish(redis, job_id, SSEEvent(type="interrupt", kind=kind, payload=payload))
            await _write_job(redis, job_id, JobState(
                job_id=job_id, status="interrupted", aria_state=_serialize(snap_state),
            ))
            resume_value = await _wait_resume(redis, job_id)
            log.info("[%s] Build resume received | value=%r", job_id, str(resume_value)[:80])
            current_input = Command(resume=resume_value)
        else:
            snapshot = await _pipeline._build_cycle.aget_state(config)
            final: ARIAState = snapshot.values  # type: ignore[assignment]
            log.info("[%s] Build cycle ended | status=%s", job_id, final.get("status"))
            return final


async def _apply_build_chunk(redis: Redis, job_id: str, chunk: dict, current_state: ARIAState) -> ARIAState:
    for node_name, update in chunk.items():
        if not isinstance(update, dict):
            log.debug("[%s] Skipping non-dict build chunk from node=%s", job_id, node_name)
            continue
        current_state = {**current_state, **update}  # type: ignore[assignment]
        log.debug("[%s] Build node completed | node=%s", job_id, node_name)
        await _publish(redis, job_id, SSEEvent(
            type="node", stage="build", node_name=node_name, status="running",
            message=f"{node_name} completed",
            aria_state=_serialize(current_state),
        ))
        await _write_job(redis, job_id, JobState(
            job_id=job_id, status=current_state.get("status", "building"),  # type: ignore[arg-type]
            aria_state=_serialize(current_state),
        ))
    return current_state


async def _wait_resume(redis: Redis, job_id: str) -> object:
    """Block until a resume signal arrives on resume:{job_id}.

    Maps the unified resume schema to what LangGraph's interrupt() expects:
    - clarify  → raw string answer
    - provide  → credentials dict
    - select   → selections dict
    - resume/retry/replan/abort → action string
    """
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"resume:{job_id}")
    log.info("[%s] Waiting for resume signal...", job_id)
    async for message in pubsub.listen():
        if message["type"] == "message":
            await pubsub.unsubscribe(f"resume:{job_id}")
            data = json.loads(message["data"])
            action = data.get("action", "")
            log.info("[%s] Resume signal | action=%s", job_id, action)
            if action == "clarify":
                return data.get("value", "")
            if action == "provide":
                return data.get("credentials", {})
            if action == "select":
                return data.get("selections", {})
            return action


def _detect_interrupt(state: ARIAState) -> tuple[str, dict]:
    if state.get("pending_credential_types"):
        return "credential", {
            "pending_types": state.get("pending_credential_types", []),
            "guide": state.get("credential_guide_payload"),
        }
    return "clarify", {"question": state.get("pending_question", "")}


async def _publish(redis: Redis, job_id: str, event: SSEEvent) -> None:
    await redis.publish(f"sse:{job_id}", event.model_dump_json(exclude_none=True))


async def _write_job(redis: Redis, job_id: str, job: JobState) -> None:
    await redis.set(f"job:{job_id}", job.model_dump_json(), ex=_JOB_TTL)


def _serialize(state: ARIAState) -> dict:
    """Convert ARIAState TypedDict to a plain JSON-safe dict."""
    return json.loads(json.dumps(dict(state), default=str))
