"""Tests for POST /jobs/{job_id}/resume endpoint."""
from __future__ import annotations

import asyncio
import json

import pytest

from src.api.schemas import JobState


pytestmark = pytest.mark.asyncio


async def _seed_job(redis, job_id: str, status: str = "interrupted") -> None:
    state = JobState(job_id=job_id, status=status)
    await redis.set(f"job:{job_id}", state.model_dump_json(), ex=86_400)


async def _read_pubsub_message(pubsub, retries: int = 10) -> dict | None:
    """Poll pubsub for a message, retrying briefly to handle async delivery."""
    for _ in range(retries):
        msg = await pubsub.get_message(ignore_subscribe_messages=True)
        if msg is not None:
            return msg
        await asyncio.sleep(0.05)
    return None


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_resume_job_returns_204(api_client, fake_redis):
    """Should return 204 when job is interrupted."""
    await _seed_job(fake_redis, "resume-1")
    response = await api_client.post("/jobs/resume-1/resume", json={"action": "clarify", "value": "use Gmail"})
    assert response.status_code == 204


@pytest.mark.integration
async def test_resume_job_publishes_to_redis(api_client, fake_redis):
    """Should publish resume payload to resume:{job_id} channel."""
    await _seed_job(fake_redis, "resume-pub")
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("resume:resume-pub")

    await api_client.post("/jobs/resume-pub/resume", json={"action": "retry"})

    msg = await _read_pubsub_message(pubsub)
    assert msg is not None
    assert json.loads(msg["data"])["action"] == "retry"
    await pubsub.unsubscribe("resume:resume-pub")


@pytest.mark.integration
async def test_resume_job_with_credentials(api_client, fake_redis):
    """Should publish credentials payload correctly."""
    await _seed_job(fake_redis, "resume-creds")
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("resume:resume-creds")
    creds = {"Gmail OAuth2": {"token": "abc"}}

    await api_client.post("/jobs/resume-creds/resume", json={"action": "provide", "credentials": creds})

    msg = await _read_pubsub_message(pubsub)
    assert msg is not None
    data = json.loads(msg["data"])
    assert data["action"] == "provide"
    assert data["credentials"] == creds
    await pubsub.unsubscribe("resume:resume-creds")


@pytest.mark.integration
async def test_resume_job_with_selections(api_client, fake_redis):
    """Should publish selections payload correctly."""
    await _seed_job(fake_redis, "resume-sel")
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("resume:resume-sel")
    selections = {"Gmail OAuth2": "cred-id-123"}

    await api_client.post("/jobs/resume-sel/resume", json={"action": "select", "selections": selections})

    msg = await _read_pubsub_message(pubsub)
    assert msg is not None
    data = json.loads(msg["data"])
    assert data["selections"] == selections
    await pubsub.unsubscribe("resume:resume-sel")


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_resume_job_404_unknown(api_client):
    """Should return 404 for unknown job_id."""
    response = await api_client.post("/jobs/ghost-job/resume", json={"action": "retry"})
    assert response.status_code == 404


@pytest.mark.integration
async def test_resume_job_409_not_interrupted(api_client, fake_redis):
    """Should return 409 when job is not in interrupted status."""
    await _seed_job(fake_redis, "active-job", status="planning")
    response = await api_client.post("/jobs/active-job/resume", json={"action": "retry"})
    assert response.status_code == 409
    assert "not interrupted" in response.json()["detail"]


@pytest.mark.integration
async def test_resume_job_missing_action(api_client, fake_redis):
    """Should return 422 when action field is absent."""
    await _seed_job(fake_redis, "resume-val")
    response = await api_client.post("/jobs/resume-val/resume", json={"value": "oops"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Edge / Contract
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_resume_job_excludes_none_fields(api_client, fake_redis):
    """Should exclude None fields from published payload."""
    await _seed_job(fake_redis, "resume-none")
    pubsub = fake_redis.pubsub()
    await pubsub.subscribe("resume:resume-none")

    await api_client.post("/jobs/resume-none/resume", json={"action": "resume"})

    msg = await _read_pubsub_message(pubsub)
    assert msg is not None
    data = json.loads(msg["data"])
    assert "value" not in data
    assert "credentials" not in data
    assert "selections" not in data
    await pubsub.unsubscribe("resume:resume-none")


@pytest.mark.integration
async def test_resume_job_409_includes_current_status(api_client, fake_redis):
    """409 detail should include the actual current status."""
    await _seed_job(fake_redis, "done-job", status="done")
    response = await api_client.post("/jobs/done-job/resume", json={"action": "retry"})
    assert response.status_code == 409
    assert "done" in response.json()["detail"]
