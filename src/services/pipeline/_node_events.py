"""Node-level SSE event emission with timing and tool metadata."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

from redis.asyncio import Redis

from src.agentic_system.shared.state import ARIAState
from src.api.schemas import JobState, SSEEvent
from src.services.pipeline._sse_helpers import publish, serialize, write_job

# Node-to-tool mapping for known preflight nodes
_NODE_TOOLS: dict[str, list[str]] = {
    "orchestrator": ["search_n8n_nodes"],
    "credential_scanner": ["list_saved_credentials", "get_credential_schema", "check_credentials_resolved"],
    "credential_guide": [],
    "credential_saver": ["n8n_credential_save"],
    "handoff": ["blueprint_builder"],
}


async def emit_node_events(
    redis: Redis, job_id: str, node_name: str, update: dict,
    current_state: ARIAState, stage: str, node_index: int, total_nodes: int,
) -> ARIAState:
    """Emit node_start + node complete events with timing and tool metadata."""
    event_id = str(uuid4())[:8]
    progress = f"{node_index} of {total_nodes}" if total_nodes > 0 else None
    tools = _NODE_TOOLS.get(node_name, [])
    ts = datetime.now(timezone.utc).isoformat()

    await _publish_start(redis, job_id, stage, node_name, event_id, tools, ts, progress)
    start = time.monotonic()
    current_state = {**current_state, **update}  # type: ignore[assignment]
    duration_ms = int((time.monotonic() - start) * 1000)

    await _publish_complete(
        redis, job_id, stage, node_name, event_id, tools, ts, progress,
        duration_ms, current_state,
    )
    return current_state


async def _publish_start(
    redis: Redis, job_id: str, stage: str, node_name: str,
    event_id: str, tools: list[str], ts: str, progress: str | None,
) -> None:
    """Publish a node_start SSE event."""
    await publish(redis, job_id, SSEEvent(
        type="node_start", stage=stage, node_name=node_name,
        event_id=event_id, message=f"{node_name} started",
        status="running", tools=tools, timestamp=ts, progress=progress,
    ))


async def _publish_complete(
    redis: Redis, job_id: str, stage: str, node_name: str,
    event_id: str, tools: list[str], ts: str, progress: str | None,
    duration_ms: int, current_state: ARIAState,
) -> None:
    """Publish a node complete SSE event and persist job state."""
    await publish(redis, job_id, SSEEvent(
        type="node", stage=stage, node_name=node_name, event_id=event_id,
        status="running", message=f"{node_name} completed",
        tools=tools, duration_ms=duration_ms, timestamp=ts,
        progress=progress, aria_state=serialize(current_state),
    ))
    await write_job(redis, job_id, JobState(
        job_id=job_id, status="planning", aria_state=serialize(current_state),
    ))
