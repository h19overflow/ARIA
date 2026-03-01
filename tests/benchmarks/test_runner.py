import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from benchmarks.adapters.base import RetrievalResult
from benchmarks.runner import run_single_query, _average_metrics, _group_by_category
from benchmarks.schema import GoldenQuery, QueryCategory, Difficulty


@pytest.fixture
def sample_query():
    return GoldenQuery(
        id="test_001",
        category=QueryCategory.NATURAL_LANGUAGE,
        query="send a slack message",
        expected_nodes=["n8n-nodes-base.slack"],
    )


@pytest.fixture
def mock_retriever():
    r = MagicMock()
    type(r).name = PropertyMock(return_value="test_retriever")
    r.setup = AsyncMock()
    r.teardown = AsyncMock()
    r.retrieve = AsyncMock(return_value=[
        RetrievalResult("n8n-nodes-base.slack", "Slack", 0.9, "node", "doc"),
    ])
    return r


@pytest.mark.asyncio
async def test_run_single_query(mock_retriever, sample_query):
    result = await run_single_query(mock_retriever, sample_query, k=5)
    assert result["query_id"] == "test_001"
    assert result["metrics"]["recall@5"] == 1.0
    assert result["metrics"]["mrr"] == 1.0
    assert "latency_ms" in result["metrics"]


def test_average_metrics():
    results = [
        {"metrics": {"recall@5": 1.0, "mrr": 1.0}},
        {"metrics": {"recall@5": 0.5, "mrr": 0.5}},
    ]
    avg = _average_metrics(results)
    assert avg["recall@5"] == 0.75
    assert avg["mrr"] == 0.75


def test_group_by_category():
    results = [
        {"category": "natural_language", "metrics": {"recall@5": 1.0}},
        {"category": "natural_language", "metrics": {"recall@5": 0.5}},
        {"category": "exact_lookup", "metrics": {"recall@5": 1.0}},
    ]
    grouped = _group_by_category(results)
    assert grouped["natural_language"]["count"] == 2
    assert grouped["natural_language"]["metrics"]["recall@5"] == 0.75
    assert grouped["exact_lookup"]["count"] == 1
