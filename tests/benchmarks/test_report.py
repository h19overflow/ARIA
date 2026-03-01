from benchmarks.report import build_comparison_table, find_winners


def test_comparison_table_empty():
    assert build_comparison_table([]) == "No results found."


def test_comparison_table_one_result():
    results = [{
        "retriever": "baseline",
        "overall": {"recall@3": 0.8, "recall@5": 0.9, "mrr": 0.75, "latency_ms": 45.2},
    }]
    table = build_comparison_table(results)
    assert "baseline" in table
    assert "0.8" in table


def test_find_winners():
    results = [
        {"retriever": "a", "overall": {"recall@5": 0.9, "latency_ms": 50}},
        {"retriever": "b", "overall": {"recall@5": 0.7, "latency_ms": 30}},
    ]
    winners = find_winners(results)
    assert "recall@5" in winners
    assert "a" in winners       # higher recall
    assert "latency_ms" in winners
    assert "b" in winners       # lower latency
