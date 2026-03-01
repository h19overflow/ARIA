from benchmarks.schema import GoldenQuery, GoldenDataset, QueryCategory, Difficulty


def test_golden_query_creation():
    q = GoldenQuery(
        id="nl_001",
        category=QueryCategory.NATURAL_LANGUAGE,
        query="send a Slack message",
        expected_nodes=["n8n-nodes-base.slack"],
    )
    assert q.id == "nl_001"
    assert q.expected_doc_type == "node"
    assert q.difficulty == Difficulty.MEDIUM


def test_golden_dataset_empty():
    ds = GoldenDataset()
    assert ds.version == "1.0"
    assert ds.queries == []
