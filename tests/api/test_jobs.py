"""Tests for GET /jobs/{job_id} and GET /jobs/{job_id}/stream."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.api.schemas import JobState


pytestmark = pytest.mark.asyncio


async def _seed_job(redis, job_id: str, status: str = "planning") -> None:
    state = JobState(job_id=job_id, status=status)
    await redis.set(f"job:{job_id}", state.model_dump_json(), ex=86_400)


# ===========================================================================
# GET /jobs/{job_id}
# ===========================================================================

@pytest.mark.integration
async def test_get_job_returns_200(api_client, fake_redis):
    """Should return 200 with job state for a known job_id."""
    await _seed_job(fake_redis, "abc-123", status="planning")
    response = await api_client.get("/jobs/abc-123")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "abc-123"
    assert body["status"] == "planning"


@pytest.mark.integration
async def test_get_job_returns_404(api_client):
    """Should return 404 for unknown job_id."""
    response = await api_client.get("/jobs/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


@pytest.mark.integration
async def test_get_job_done_status(api_client, fake_redis):
    """Should return done status and aria_state when job completed."""
    state = JobState(job_id="done-1", status="done", aria_state={"result": "ok"})
    await fake_redis.set("job:done-1", state.model_dump_json(), ex=86_400)
    response = await api_client.get("/jobs/done-1")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["result"] == {"result": "ok"}


@pytest.mark.integration
async def test_get_job_error_state(api_client, fake_redis):
    """Should expose error message when job is in error state."""
    state = JobState(job_id="err-1", status="error", error="pipeline failed")
    await fake_redis.set("job:err-1", state.model_dump_json(), ex=86_400)
    response = await api_client.get("/jobs/err-1")
    assert response.status_code == 200
    assert response.json()["error"] == "pipeline failed"


@pytest.mark.integration
async def test_get_job_response_schema(api_client, fake_redis):
    """Response schema must include job_id, status, result, error."""
    await _seed_job(fake_redis, "schema-job")
    body = (await api_client.get("/jobs/schema-job")).json()
    assert {"job_id", "status", "result", "error"}.issubset(body.keys())


# ===========================================================================
# GET /jobs/{job_id}/stream
# ===========================================================================

@pytest.mark.integration
async def test_stream_job_404_for_unknown(api_client):
    """Should return 404 when job_id not found."""
    response = await api_client.get("/jobs/unknown-stream/stream")
    assert response.status_code == 404


@pytest.mark.integration
async def test_stream_job_returns_event_stream_content_type(api_client, fake_redis):
    """Should return 200 with text/event-stream content-type."""
    await _seed_job(fake_redis, "stream-1")

    async def _instant_gen(job_id: str, redis):  # noqa: ARG001
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    with patch("src.api.routers.jobs._sse_generator", side_effect=_instant_gen):
        async with api_client.stream("GET", "/jobs/stream-1/stream") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            async for _ in resp.aiter_lines():
                pass


