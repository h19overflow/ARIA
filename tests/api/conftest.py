"""Shared fixtures for API tests."""
from __future__ import annotations

import pytest
import pytest_asyncio
import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.api.lifespan.redis import get_redis


@pytest_asyncio.fixture
async def fake_redis():
    """Provides an in-memory async Redis instance."""
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def api_client(fake_redis):
    """AsyncClient with the real FastAPI app and Redis overridden."""
    app.dependency_overrides[get_redis] = lambda: fake_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
