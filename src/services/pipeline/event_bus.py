"""EventBus — typed SSE event emitter for build cycle nodes."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from redis.asyncio import Redis

from src.api.schemas import SSEEvent

log = logging.getLogger("aria.event_bus")


def get_event_bus(state: dict[str, Any]) -> BuildEventBus | None:
    """Create a BuildEventBus from state, or None if job_id is missing."""
    job_id = state.get("job_id", "")
    if not job_id:
        return None
    from src.api.lifespan.redis import get_redis_instance
    try:
        return BuildEventBus(get_redis_instance(), job_id)
    except RuntimeError:
        return None


class BuildEventBus:
    """Emit typed SSE events from any build cycle node."""

    def __init__(self, redis: Redis, job_id: str) -> None:
        self._redis = redis
        self._job_id = job_id

    async def emit_start(self, stage: str, node_name: str, message: str) -> None:
        """Emit a node_start event."""
        await self._publish(SSEEvent(
            type="node_start",
            stage=stage,
            node_name=node_name,
            message=message,
            status="running",
            event_id=self._make_event_id(),
            timestamp=self._now(),
        ))

    async def emit_complete(
        self, stage: str, node_name: str, status: str,
        message: str, duration_ms: int = 0,
        aria_state: dict | None = None,
    ) -> None:
        """Emit a node complete event with success/error status."""
        await self._publish(SSEEvent(
            type="node",
            stage=stage,
            node_name=node_name,
            message=message,
            status=status,
            duration_ms=duration_ms,
            event_id=self._make_event_id(),
            timestamp=self._now(),
            aria_state=aria_state,
        ))

    async def emit_warning(self, stage: str, node_name: str, message: str) -> None:
        """Emit a warning event (e.g. credential auto-attach)."""
        await self._publish(SSEEvent(
            type="warning",
            stage=stage,
            node_name=node_name,
            message=message,
            status="warning",
            event_id=self._make_event_id(),
            timestamp=self._now(),
        ))

    async def emit_progress(
        self, stage: str, current: int, total: int, message: str,
    ) -> None:
        """Emit a progress update (e.g. 'Node 2 of 5 built')."""
        await self._publish(SSEEvent(
            type="node",
            stage=stage,
            message=message,
            status="running",
            progress=f"{current} of {total}",
            event_id=self._make_event_id(),
            timestamp=self._now(),
        ))

    async def _publish(self, event: SSEEvent) -> None:
        """Publish event to Redis pubsub channel."""
        await self._redis.publish(
            f"sse:{self._job_id}",
            event.model_dump_json(exclude_none=True),
        )

    @staticmethod
    def _make_event_id() -> str:
        return str(uuid4())[:8]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
