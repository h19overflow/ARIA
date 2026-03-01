from __future__ import annotations

from src.boundary.chroma.store import ChromaStore
from benchmarks.adapters.base import BaseRetriever, RetrievalResult


class ChromaSemanticRetriever(BaseRetriever):
    """Wraps ChromaStore.query_n8n_documents (semantic only)."""

    def __init__(self) -> None:
        self._store: ChromaStore | None = None

    @property
    def name(self) -> str:
        return "baseline_semantic"

    async def setup(self) -> None:
        self._store = ChromaStore()
        await self._store.connect()

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        doc_type: str | None = None,
    ) -> list[RetrievalResult]:
        raw = await self._store.query_n8n_documents(
            query=query, n_results=k, doc_type=doc_type,
        )
        return [_to_result(r) for r in raw]

    async def teardown(self) -> None:
        if self._store:
            await self._store.disconnect()


class ChromaHybridRetriever(BaseRetriever):
    """Wraps ChromaStore.hybrid_query_n8n_documents (BM25 + RRF)."""

    def __init__(self, alpha: float | None = None) -> None:
        self._store: ChromaStore | None = None
        self._alpha = alpha

    @property
    def name(self) -> str:
        suffix = f"_alpha{self._alpha}" if self._alpha is not None else ""
        return f"baseline_hybrid{suffix}"

    async def setup(self) -> None:
        self._store = ChromaStore()
        await self._store.connect()

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        doc_type: str | None = None,
    ) -> list[RetrievalResult]:
        raw = await self._store.hybrid_query_n8n_documents(
            query=query, n_results=k, doc_type=doc_type, alpha=self._alpha,
        )
        return [_to_result(r) for r in raw]

    async def teardown(self) -> None:
        if self._store:
            await self._store.disconnect()


def _to_result(raw: dict) -> RetrievalResult:
    return RetrievalResult(
        node_type=raw.get("node_type", ""),
        name=raw.get("name", ""),
        score=raw.get("score", 0.0),
        doc_type=raw.get("doc_type", ""),
        document=raw.get("document", ""),
    )
