"""
FastAPI dependency + lifespan helper for the Redis async client.
"""

from fastapi import Request
from redis.asyncio import Redis

from src.api.settings import settings

_client: Redis | None = None


async def startup() -> None:
    global _client
    _client = Redis.from_url(settings.redis_url, decode_responses=True)
    await _client.ping()


async def shutdown() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_redis(request: Request) -> Redis:  # noqa: ARG001
    """FastAPI dependency — injects the shared Redis async client."""
    if _client is None:
        raise RuntimeError("Redis client not initialised — lifespan not running")
    return _client
