from unittest.mock import AsyncMock, MagicMock
import pytest

from benchmarks.adapters.base import RetrievalResult
from benchmarks.adapters.rerank_adapter import RerankRetriever


def _mock_inner():
    inner = MagicMock()
    inner.name = "baseline_hybrid"
    inner.setup = AsyncMock()
    inner.teardown = AsyncMock()
    inner.retrieve = AsyncMock(return_value=[
        RetrievalResult("n8n-nodes-base.slack", "Slack", 0.8, "node", "Slack doc"),
        RetrievalResult("n8n-nodes-base.gmail", "Gmail", 0.6, "node", "Gmail doc"),
    ])
    return inner


def test_rerank_name():
    inner = _mock_inner()
    r = RerankRetriever(inner, reranker="flashrank")
    assert r.name == "baseline_hybrid+rerank_flashrank"


def test_rerank_bge_name():
    inner = _mock_inner()
    r = RerankRetriever(inner, reranker="bge_reranker")
    assert r.name == "baseline_hybrid+rerank_bge_reranker"


@pytest.mark.asyncio
async def test_retrieve_empty_candidates_returns_empty():
    inner = _mock_inner()
    inner.retrieve = AsyncMock(return_value=[])
    r = RerankRetriever(inner, reranker="flashrank")
    r._reranker = MagicMock()
    results = await r.retrieve("test query", k=5)
    assert results == []


@pytest.mark.asyncio
async def test_retrieve_calls_inner_with_k_times_3():
    inner = _mock_inner()
    mock_reranker = MagicMock()
    mock_reranker.score = MagicMock(return_value=[0.9, 0.7])
    r = RerankRetriever(inner, reranker="flashrank")
    r._reranker = mock_reranker
    await r.retrieve("test query", k=2)
    inner.retrieve.assert_called_once_with(query="test query", k=6, doc_type=None)


@pytest.mark.asyncio
async def test_retrieve_reranks_and_returns_top_k():
    inner = _mock_inner()
    mock_reranker = MagicMock()
    # Gmail (index 1) gets higher score so it should rank first
    mock_reranker.score = MagicMock(return_value=[0.3, 0.95])
    r = RerankRetriever(inner, reranker="flashrank")
    r._reranker = mock_reranker
    results = await r.retrieve("test query", k=1)
    assert len(results) == 1
    assert results[0].name == "Gmail"
    assert results[0].score == 0.95


@pytest.mark.asyncio
async def test_teardown_clears_reranker():
    inner = _mock_inner()
    r = RerankRetriever(inner, reranker="flashrank")
    r._reranker = MagicMock()
    await r.teardown()
    assert r._reranker is None
    inner.teardown.assert_called_once()


@pytest.mark.asyncio
async def test_setup_calls_inner_setup():
    inner = _mock_inner()
    r = RerankRetriever(inner, reranker="flashrank")
    # Patch _build_flashrank to avoid real import
    import benchmarks.adapters.rerank_adapter as mod
    original = mod._build_flashrank
    mod._build_flashrank = MagicMock(return_value=MagicMock())
    try:
        await r.setup()
        inner.setup.assert_called_once()
    finally:
        mod._build_flashrank = original
