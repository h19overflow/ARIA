"""Shared SSE/Redis helpers used by preflight_service and build_service."""
from __future__ import annotations

import asyncio
import json
import logging

from langgraph.types import Command
from redis.asyncio import Redis

from src.agentic_system.shared.state import ARIAState
from src.api.schemas import JobState, SSEEvent

log = logging.getLogger("aria.services")

_JOB_TTL = 86_400  # 24 hours


def coerce_state(inp: ARIAState | Command) -> ARIAState:  # type: ignore[type-arg]
    """Return inp as ARIAState — Commands don't have state fields."""
    if isinstance(inp, dict):
        return inp  # type: ignore[return-value]
    return {}  # type: ignore[return-value]


def build_initial_state(description: str) -> ARIAState:
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


def detect_interrupt(state: ARIAState) -> tuple[str, dict]:
    if state.get("pending_credential_types"):
        return "credential", {
            "pending_types": state.get("pending_credential_types", []),
            "guide": state.get("credential_guide_payload"),
        }
    return "clarify", {"question": state.get("pending_question", "")}


def serialize(state: ARIAState) -> dict:
    """Convert ARIAState TypedDict to a plain JSON-safe dict."""
    return json.loads(json.dumps(dict(state), default=str))


async def publish(redis: Redis, job_id: str, event: SSEEvent) -> None:
    await redis.publish(f"sse:{job_id}", event.model_dump_json(exclude_none=True))


async def write_job(redis: Redis, job_id: str, job: JobState) -> None:
    await redis.set(f"job:{job_id}", job.model_dump_json(), ex=_JOB_TTL)


async def apply_chunk(
    redis: Redis, job_id: str, chunk: dict, current_state: ARIAState, stage: str,
) -> ARIAState:
    """Merge a streaming chunk into state and publish node SSE events."""
    for node_name, update in chunk.items():
        if not isinstance(update, dict):
            log.debug("[%s] Skipping non-dict chunk from node=%s type=%s", job_id, node_name, type(update).__name__)
            continue
        current_state = {**current_state, **update}  # type: ignore[assignment]
        log.debug("[%s] Node completed | stage=%s node=%s", job_id, stage, node_name)
        await publish(redis, job_id, SSEEvent(
            type="node", stage=stage, node_name=node_name, status="running",
            message=f"{node_name} completed",
            aria_state=serialize(current_state),
        ))
        await write_job(redis, job_id, JobState(
            job_id=job_id, status="planning", aria_state=serialize(current_state),
        ))
    return current_state


async def apply_build_chunk(redis: Redis, job_id: str, chunk: dict, current_state: ARIAState) -> ARIAState:
    for node_name, update in chunk.items():
        if not isinstance(update, dict):
            log.debug("[%s] Skipping non-dict build chunk from node=%s", job_id, node_name)
            continue
        current_state = {**current_state, **update}  # type: ignore[assignment]
        log.debug("[%s] Build node completed | node=%s", job_id, node_name)
        await publish(redis, job_id, SSEEvent(
            type="node", stage="build", node_name=node_name, status="running",
            message=f"{node_name} completed",
            aria_state=serialize(current_state),
        ))
        await write_job(redis, job_id, JobState(
            job_id=job_id, status=current_state.get("status", "building"),  # type: ignore[arg-type]
            aria_state=serialize(current_state),
        ))
    return current_state


async def wait_resume(redis: Redis, job_id: str) -> object:
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
