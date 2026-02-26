"""Phase 1 Preflight service — orchestrates agent and state."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict

from redis.asyncio import Redis

from src.agentic_system.preflight.agent import PreflightAgent
from src.agentic_system.preflight.state import get_preflight_state

logger = logging.getLogger(__name__)


async def initialize_preflight(
    conversation_id: str,
    redis: Redis,
    agent: PreflightAgent,
) -> str:
    """Read Phase 0 notes from Redis, create PreflightState, return preflight_id."""
    raw = await redis.get(f"conversation:{conversation_id}")
    if not raw:
        raise ValueError(f"Conversation {conversation_id} not found in Redis")

    try:
        data = json.loads(raw)
        conversation_notes = data.get("notes", {})
    except (json.JSONDecodeError, AttributeError) as e:
        raise ValueError(f"Failed to parse conversation state: {e}") from e

    if not data.get("committed"):
        raise ValueError(
            "Phase 0 conversation is not committed yet. "
            "Complete the requirements conversation first."
        )

    preflight_id = str(uuid.uuid4())
    await agent.initialize_preflight(preflight_id, conversation_id, conversation_notes)
    logger.info(
        "Preflight session created | preflight_id=%s conversation_id=%s",
        preflight_id,
        conversation_id,
    )
    return preflight_id


async def process_preflight_message(
    preflight_id: str,
    user_message: str,
    agent: PreflightAgent,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Delegate to agent and stream SSE events."""
    async for event in agent.process_message(preflight_id, user_message):
        yield event


async def get_preflight_status(preflight_id: str) -> Dict[str, Any]:
    """Return current preflight status and notes."""
    state = await get_preflight_state(preflight_id)
    if not state:
        raise ValueError(f"Preflight session not found: {preflight_id}")
    return {
        "committed": state.committed,
        "notes": state.notes.model_dump(),
    }
