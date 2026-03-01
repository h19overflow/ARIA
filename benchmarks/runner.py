"""
Benchmark runner: execute a retriever against the golden dataset, collect metrics + latency.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from benchmarks.adapters.base import BaseRetriever
from benchmarks.metrics import compute_all_metrics
from benchmarks.schema import GoldenDataset, GoldenQuery

RESULTS_DIR = Path(__file__).parent / "results"


async def run_single_query(
    retriever: BaseRetriever,
    query: GoldenQuery,
    k: int = 10,
) -> dict:
    """Run one query, return metrics + latency."""
    start = time.perf_counter()
    results = await retriever.retrieve(
        query=query.query,
        k=k,
        doc_type=query.expected_doc_type if query.expected_doc_type != "node" else "node",
    )
    latency_ms = (time.perf_counter() - start) * 1000

    retrieved_types = [r.node_type for r in results]
    metrics = compute_all_metrics(retrieved_types, query.expected_nodes)
    metrics["latency_ms"] = round(latency_ms, 2)

    return {
        "query_id": query.id,
        "category": query.category.value if hasattr(query.category, "value") else query.category,
        "query": query.query,
        "expected": query.expected_nodes,
        "retrieved": retrieved_types,
        "metrics": metrics,
    }


async def run_benchmark(
    retriever: BaseRetriever,
    dataset: GoldenDataset,
    k: int = 10,
) -> dict:
    """Run all queries against a retriever, aggregate results."""
    await retriever.setup()
    try:
        query_results = []
        for query in dataset.queries:
            result = await run_single_query(retriever, query, k=k)
            query_results.append(result)
        return _aggregate_results(retriever.name, query_results)
    finally:
        await retriever.teardown()


def _aggregate_results(
    retriever_name: str,
    query_results: list[dict],
) -> dict:
    """Aggregate per-query metrics into overall + per-category summaries."""
    overall = _average_metrics(query_results)
    by_category = _group_by_category(query_results)
    return {
        "retriever": retriever_name,
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(query_results),
        "overall": overall,
        "by_category": by_category,
        "queries": query_results,
    }


def _average_metrics(results: list[dict]) -> dict[str, float]:
    """Average all metric keys across results."""
    if not results:
        return {}
    keys = results[0]["metrics"].keys()
    return {
        key: round(
            sum(r["metrics"][key] for r in results) / len(results), 4,
        )
        for key in keys
    }


def _group_by_category(results: list[dict]) -> dict[str, dict]:
    """Group results by category and average metrics per group."""
    groups: dict[str, list[dict]] = {}
    for r in results:
        cat = r["category"]
        groups.setdefault(cat, []).append(r)
    return {
        cat: {
            "count": len(items),
            "metrics": _average_metrics(items),
        }
        for cat, items in groups.items()
    }


def save_results(results: dict) -> Path:
    """Write results to benchmarks/results/."""
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = results["retriever"].replace("+", "_")
    path = RESULTS_DIR / f"{ts}_{name}.json"
    path.write_text(json.dumps(results, indent=2))
    return path
