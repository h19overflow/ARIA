from benchmarks.adapters.chunked_adapter import ChunkedRetriever
from benchmarks.adapters.base import BaseRetriever


def test_fixed_chunk_name():
    r = ChunkedRetriever(chunk_size=512, strategy="fixed")
    assert r.name == "chunked_512"


def test_parent_child_name():
    r = ChunkedRetriever(strategy="parent_child")
    assert r.name == "chunked_parent_child"


def test_chunked_is_base():
    r = ChunkedRetriever()
    assert isinstance(r, BaseRetriever)
