"""
FastAPI dependency + lifespan helper for the shared N8nClient.
"""

from fastapi import Request

from src.boundary.n8n.client import N8nClient

_client: N8nClient | None = None


async def startup() -> None:
    global _client
    _client = N8nClient()
    await _client.connect()


async def shutdown() -> None:
    global _client
    if _client is not None:
        await _client.disconnect()
        _client = None


def get_n8n(request: Request) -> N8nClient:  # noqa: ARG001
    """FastAPI dependency — injects the shared N8nClient."""
    if _client is None:
        raise RuntimeError("N8nClient not initialised — lifespan not running")
    return _client
