from benchmarks.adapters.huggingface_adapter import HuggingFaceRetriever
from benchmarks.adapters.base import BaseRetriever


def test_hf_retriever_name():
    r = HuggingFaceRetriever("BAAI/bge-m3", search_mode="hybrid")
    assert r.name == "hf_bge-m3_hybrid"


def test_hf_retriever_semantic_name():
    r = HuggingFaceRetriever("intfloat/e5-large-v2", search_mode="semantic")
    assert r.name == "hf_e5-large-v2_semantic"


def test_hf_retriever_is_base():
    r = HuggingFaceRetriever("thenlper/gte-large")
    assert isinstance(r, BaseRetriever)
