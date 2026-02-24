from __future__ import annotations

import json

from langgraph.errors import GraphInterrupt
from redis.asyncio import Redis

from src.agentic_system.graph import ARIAPipeline
from src.agentic_system.shared.state import ARIAState
from src.api.schemas import JobState, SSEEvent

_pipeline = ARIAPipeline()
_JOB_TTL = 86_400  # 24 hours


async def run_job(job_id: str, description: str, redis: Redis) -> None:
    """Entry point — called as asyncio.create_task from the workflows router."""
    config = {"configurable": {"thread_id": job_id}}
    initial_state = _build_initial_state(description)
    try:
        await _write_job(redis, job_id, JobState(job_id=job_id, status="planning"))
        state = await _stream_preflight(job_id, initial_state, config, redis)
        state = await _stream_build(job_id, state, config, redis)
        await _publish(redis, job_id, SSEEvent(type="done", aria_state=_serialize(state)))
        await _write_job(redis, job_id, JobState(job_id=job_id, status="done", aria_state=_serialize(state)))
    except Exception as exc:
        msg = str(exc)
        await _publish(redis, job_id, SSEEvent(type="error", message=msg))
        await _write_job(redis, job_id, JobState(job_id=job_id, status="failed", error=msg))


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
    """Stream preflight graph, handling HITL interrupts."""
    current_state = state
    while True:
        try:
            async for chunk in _pipeline._preflight.astream(current_state, config=config):
                current_state = await _apply_chunk(redis, job_id, chunk, current_state, "preflight")
            snapshot = await _pipeline._preflight.aget_state(config)
            return snapshot.values  # type: ignore[return-value]
        except GraphInterrupt:
            current_state = await _handle_interrupt(redis, job_id, config)


async def _handle_interrupt(redis: Redis, job_id: str, config: dict) -> ARIAState:
    """Snapshot state after interrupt, publish SSE, wait for resume signal."""
    snapshot = await _pipeline._preflight.aget_state(config)
    current_state: ARIAState = snapshot.values  # type: ignore[assignment]
    kind, payload = _detect_interrupt(current_state)
    await _publish(redis, job_id, SSEEvent(type="interrupt", kind=kind, payload=payload))
    await _write_job(redis, job_id, JobState(
        job_id=job_id, status="interrupted", aria_state=_serialize(current_state),
    ))
    resume_value = await _wait_resume(redis, job_id)
    from langgraph.types import Command  # noqa: PLC0415
    return await _pipeline._preflight.ainvoke(Command(resume=resume_value), config=config)


async def _apply_chunk(
    redis: Redis, job_id: str, chunk: dict, current_state: ARIAState, stage: str,
) -> ARIAState:
    """Merge a streaming chunk into state and publish node SSE events."""
    for node_name, update in chunk.items():
        current_state = {**current_state, **update}  # type: ignore[assignment]
        await _publish(redis, job_id, SSEEvent(
            type="node", stage=stage, node_name=node_name, status="running",
            message=f"{node_name} completed",
        ))
        await _write_job(redis, job_id, JobState(
            job_id=job_id, status="planning", aria_state=_serialize(current_state),
        ))
    return current_state


async def _stream_build(job_id: str, state: ARIAState, config: dict, redis: Redis) -> ARIAState:
    """Stream build cycle graph."""
    current_state = state
    async for chunk in _pipeline._build_cycle.astream(current_state, config=config):
        current_state = await _apply_build_chunk(redis, job_id, chunk, current_state)
    snapshot = await _pipeline._build_cycle.aget_state(config)
    return snapshot.values  # type: ignore[return-value]


async def _apply_build_chunk(redis: Redis, job_id: str, chunk: dict, current_state: ARIAState) -> ARIAState:
    for node_name, update in chunk.items():
        current_state = {**current_state, **update}  # type: ignore[assignment]
        await _publish(redis, job_id, SSEEvent(
            type="node", stage="build", node_name=node_name, status="running",
            message=f"{node_name} completed",
        ))
        await _write_job(redis, job_id, JobState(
            job_id=job_id, status=current_state.get("status", "building"),  # type: ignore[arg-type]
            aria_state=_serialize(current_state),
        ))
    return current_state


async def _wait_resume(redis: Redis, job_id: str) -> object:
    """Block until a resume signal is published on resume:{job_id}."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"resume:{job_id}")
    async for message in pubsub.listen():
        if message["type"] == "message":
            await pubsub.unsubscribe(f"resume:{job_id}")
            return json.loads(message["data"])


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
