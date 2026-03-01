"""
Retrieval metrics: Recall@K, Precision@K, MRR, Hit Rate@K.
All functions take lists of node_type strings.
"""
from __future__ import annotations


def recall_at_k(
    retrieved: list[str],
    expected: list[str],
    k: int = 5,
) -> float:
    """Fraction of expected nodes found in top-K retrieved."""
    if not expected:
        return 1.0
    top_k = set(retrieved[:k])
    hits = len(top_k & set(expected))
    return hits / len(expected)


def precision_at_k(
    retrieved: list[str],
    expected: list[str],
    k: int = 5,
) -> float:
    """Fraction of top-K retrieved that are expected."""
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = len(set(top_k) & set(expected))
    return hits / len(top_k)


def mean_reciprocal_rank(
    retrieved: list[str],
    expected: list[str],
) -> float:
    """Reciprocal rank of the first correct result."""
    expected_set = set(expected)
    for i, node in enumerate(retrieved):
        if node in expected_set:
            return 1.0 / (i + 1)
    return 0.0


def hit_rate_at_k(
    retrieved: list[str],
    expected: list[str],
    k: int = 5,
) -> float:
    """1.0 if any expected node appears in top-K, else 0.0."""
    top_k = set(retrieved[:k])
    return 1.0 if top_k & set(expected) else 0.0


def compute_all_metrics(
    retrieved: list[str],
    expected: list[str],
) -> dict[str, float]:
    """Compute all metrics at K=3, 5, 10."""
    result = {}
    for k in (3, 5, 10):
        result[f"recall@{k}"] = recall_at_k(retrieved, expected, k)
        result[f"precision@{k}"] = precision_at_k(retrieved, expected, k)
        result[f"hit_rate@{k}"] = hit_rate_at_k(retrieved, expected, k)
    result["mrr"] = mean_reciprocal_rank(retrieved, expected)
    return result
