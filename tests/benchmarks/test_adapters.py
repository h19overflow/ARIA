from benchmarks.adapters.base import BaseRetriever, RetrievalResult
from benchmarks.adapters.chroma_adapter import (
    ChromaSemanticRetriever,
    ChromaHybridRetriever,
)


def test_retrieval_result_creation():
    r = RetrievalResult(
        node_type="n8n-nodes-base.slack",
        name="Slack",
        score=0.85,
        doc_type="node",
        document="Slack node template",
    )
    assert r.node_type == "n8n-nodes-base.slack"
    assert r.score == 0.85


def test_semantic_retriever_is_base():
    retriever = ChromaSemanticRetriever()
    assert isinstance(retriever, BaseRetriever)
    assert retriever.name == "baseline_semantic"


def test_hybrid_retriever_is_base():
    retriever = ChromaHybridRetriever(alpha=0.5)
    assert isinstance(retriever, BaseRetriever)
    assert retriever.name == "baseline_hybrid_alpha0.5"


def test_hybrid_retriever_auto_alpha():
    retriever = ChromaHybridRetriever()
    assert retriever.name == "baseline_hybrid"
