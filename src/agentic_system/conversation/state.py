import logging
import os
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from pydantic import BaseModel
from redis.exceptions import RedisError

from .schemas import ConversationNotes

logger = logging.getLogger(__name__)

# In-memory fallback cache: maps conversation_id to JSON string of state
_FALLBACK_CACHE: Dict[str, str] = {}

# Initialize async Redis client
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


class ConversationState(BaseModel):
    """
    Represents the state of a Phase 0 conversation.
    """
    conversation_id: str
    messages: List[Dict[str, Any]]
    notes: ConversationNotes
    committed: bool = False


async def save_state(state: ConversationState) -> None:
    """
    Save the conversation state to Redis.
    Falls back to an in-memory cache if Redis is unavailable.
    """
    state_json = state.model_dump_json()
    key = f"conversation:{state.conversation_id}"
    
    try:
        await redis_client.set(key, state_json, ex=86_400)
        # If successfully saved to Redis, remove from fallback cache if it exists
        if state.conversation_id in _FALLBACK_CACHE:
            del _FALLBACK_CACHE[state.conversation_id]
    except RedisError as e:
        logger.warning(f"Redis unavailable, using in-memory cache for save_state: {e}")
        _FALLBACK_CACHE[state.conversation_id] = state_json


async def get_state(conversation_id: str) -> Optional[ConversationState]:
    """
    Retrieve the conversation state from Redis.
    Falls back to the in-memory cache if Redis is unavailable or if the key
    was saved there during a temporary Redis outage.
    """
    key = f"conversation:{conversation_id}"
    state_json = None
    
    try:
        state_json = await redis_client.get(key)
    except RedisError as e:
        logger.warning(f"Redis unavailable, using in-memory cache for get_state: {e}")
    
    # If not found in Redis (or Redis failed), check the fallback cache
    if not state_json:
        state_json = _FALLBACK_CACHE.get(conversation_id)
        
    if state_json:
        return ConversationState.model_validate_json(state_json)
        
    return None
