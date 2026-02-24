"""Tests for POST /workflows endpoint."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Positive
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_workflow_returns_202(api_client):
    """Should return 202 with job_id and status=planning."""
    with patch("src.api.routers.workflows.pipeline_service.run_job", new_callable=AsyncMock):
        response = await api_client.post("/workflows", json={"description": "Send a Slack message"})

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "planning"
    assert "job_id" in body
    assert len(body["job_id"]) == 36  # UUID format


@pytest.mark.integration
async def test_create_workflow_stores_job_in_redis(api_client, fake_redis):
    """Should persist initial JobState in Redis with TTL."""
    with patch("src.api.routers.workflows.pipeline_service.run_job", new_callable=AsyncMock):
        response = await api_client.post("/workflows", json={"description": "Ping webhook"})

    job_id = response.json()["job_id"]
    raw = await fake_redis.get(f"job:{job_id}")
    assert raw is not None
    state = json.loads(raw)
    assert state["job_id"] == job_id
    assert state["status"] == "planning"


@pytest.mark.integration
async def test_create_workflow_unique_job_ids(api_client):
    """Each submission should produce a distinct job_id."""
    with patch("src.api.routers.workflows.pipeline_service.run_job", new_callable=AsyncMock):
        r1 = await api_client.post("/workflows", json={"description": "Task A"})
        r2 = await api_client.post("/workflows", json={"description": "Task B"})

    assert r1.json()["job_id"] != r2.json()["job_id"]


# ---------------------------------------------------------------------------
# Negative
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_workflow_missing_description(api_client):
    """Should return 422 when description is missing."""
    response = await api_client.post("/workflows", json={})
    assert response.status_code == 422


@pytest.mark.integration
async def test_create_workflow_empty_body(api_client):
    """Should return 422 when body is empty."""
    response = await api_client.post("/workflows", content=b"")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Edge Case
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_workflow_long_description(api_client):
    """Should accept very long description strings."""
    description = "x" * 5000
    with patch("src.api.routers.workflows.pipeline_service.run_job", new_callable=AsyncMock):
        response = await api_client.post("/workflows", json={"description": description})
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_workflow_response_schema(api_client):
    """Response must include exactly job_id and status fields."""
    with patch("src.api.routers.workflows.pipeline_service.run_job", new_callable=AsyncMock):
        response = await api_client.post("/workflows", json={"description": "schema check"})

    body = response.json()
    assert set(body.keys()) == {"job_id", "status"}
    assert isinstance(body["job_id"], str)
    assert isinstance(body["status"], str)
