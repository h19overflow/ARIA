import pytest
from benchmarks.metrics import (
    recall_at_k,
    precision_at_k,
    mean_reciprocal_rank,
    hit_rate_at_k,
    compute_all_metrics,
)


def test_recall_at_k_perfect():
    retrieved = ["slack", "gmail"]
    expected = ["slack", "gmail"]
    assert recall_at_k(retrieved, expected, k=5) == 1.0


def test_recall_at_k_partial():
    retrieved = ["slack", "telegram"]
    expected = ["slack", "gmail"]
    assert recall_at_k(retrieved, expected, k=5) == 0.5


def test_recall_at_k_miss():
    retrieved = ["telegram", "discord"]
    expected = ["slack", "gmail"]
    assert recall_at_k(retrieved, expected, k=5) == 0.0


def test_precision_at_k():
    retrieved = ["slack", "gmail", "telegram"]
    expected = ["slack", "gmail"]
    assert precision_at_k(retrieved, expected, k=3) == pytest.approx(2 / 3)


def test_mrr_first():
    retrieved = ["slack", "gmail"]
    expected = ["slack"]
    assert mean_reciprocal_rank(retrieved, expected) == 1.0


def test_mrr_second():
    retrieved = ["telegram", "slack"]
    expected = ["slack"]
    assert mean_reciprocal_rank(retrieved, expected) == 0.5


def test_mrr_miss():
    retrieved = ["telegram", "discord"]
    expected = ["slack"]
    assert mean_reciprocal_rank(retrieved, expected) == 0.0


def test_hit_rate_at_k_hit():
    retrieved = ["telegram", "slack"]
    expected = ["slack"]
    assert hit_rate_at_k(retrieved, expected, k=5) == 1.0


def test_hit_rate_at_k_miss():
    retrieved = ["telegram", "discord"]
    expected = ["slack"]
    assert hit_rate_at_k(retrieved, expected, k=5) == 0.0


def test_compute_all_metrics():
    retrieved = ["slack", "telegram", "gmail"]
    expected = ["slack", "gmail"]
    m = compute_all_metrics(retrieved, expected)
    assert "recall@3" in m
    assert "recall@5" in m
    assert "recall@10" in m
    assert "precision@3" in m
    assert "mrr" in m
    assert "hit_rate@3" in m
