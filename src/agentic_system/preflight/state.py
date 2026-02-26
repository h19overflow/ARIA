"""Preflight agent state — Redis persistence."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from pydantic import BaseModel
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

_FALLBACK_CACHE: Dict[str, str] = {}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


class PreflightNotes(BaseModel):
    required_nodes: List[str] = []
    required_integrations: List[str] = []   # service names from Phase 0
    resolved_credential_ids: Dict[str, str] = {}
    pending_credential_types: List[str] = []
    summary: str = ""
    committed: bool = False
    raw_notes: Dict[str, str] = {}


class PreflightState(BaseModel):
    preflight_id: str
    conversation_id: Optional[str] = None
    messages: List[Dict[str, Any]]
    notes: PreflightNotes
    committed: bool = False


async def save_preflight_state(state: PreflightState) -> None:
    """Save PreflightState to Redis with 24h TTL; fall back to memory."""
    state_json = state.model_dump_json()
    key = f"preflight:{state.preflight_id}"
    try:
        await redis_client.set(key, state_json, ex=86_400)
        _FALLBACK_CACHE.pop(state.preflight_id, None)
    except RedisError as e:
        logger.warning("Redis unavailable for save_preflight_state: %s", e)
        _FALLBACK_CACHE[state.preflight_id] = state_json


async def get_preflight_state(preflight_id: str) -> Optional[PreflightState]:
    """Load PreflightState from Redis; fall back to memory cache."""
    key = f"preflight:{preflight_id}"
    state_json = None
    try:
        state_json = await redis_client.get(key)
    except RedisError as e:
        logger.warning("Redis unavailable for get_preflight_state: %s", e)
    if not state_json:
        state_json = _FALLBACK_CACHE.get(preflight_id)
    if state_json:
        return PreflightState.model_validate_json(state_json)
    return None
