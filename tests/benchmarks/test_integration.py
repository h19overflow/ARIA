"""
Integration test: run baseline retriever against live ChromaDB.
Requires: ChromaDB running on localhost:8001 with n8n_documents collection.
Skip with: pytest -m "not integration"
"""
import pytest

from benchmarks.adapters.chroma_adapter import ChromaHybridRetriever
from benchmarks.schema import GoldenQuery, GoldenDataset, QueryCategory
from benchmarks.runner import run_benchmark


@pytest.mark.integration
@pytest.mark.asyncio
async def test_baseline_hybrid_against_live_chroma():
    dataset = GoldenDataset(queries=[
        GoldenQuery(
            id="smoke_001",
            category=QueryCategory.EXACT_LOOKUP,
            query="Slack node",
            expected_nodes=["n8n-nodes-base.slack"],
        ),
        GoldenQuery(
            id="smoke_002",
            category=QueryCategory.NATURAL_LANGUAGE,
            query="send a message to a chat channel",
            expected_nodes=["n8n-nodes-base.slack"],
        ),
    ])

    retriever = ChromaHybridRetriever()
    results = await run_benchmark(retriever, dataset)

    assert results["total_queries"] == 2
    assert results["overall"]["recall@5"] > 0.0
    assert results["overall"]["latency_ms"] > 0
    print(f"Smoke test recall@5: {results['overall']['recall@5']}")
