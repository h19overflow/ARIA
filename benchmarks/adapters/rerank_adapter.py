"""
Wraps any BaseRetriever and adds a reranking stage.
Supported rerankers: BGE-reranker-v2-m3 (HuggingFace), FlashRank (lightweight).
"""
from __future__ import annotations

from benchmarks.adapters.base import BaseRetriever, RetrievalResult


class RerankRetriever(BaseRetriever):
    """Decorator: retrieves K*3 from inner retriever, reranks, returns top K."""

    def __init__(
        self,
        inner: BaseRetriever,
        reranker: str = "flashrank",  # "flashrank" or "bge_reranker"
    ) -> None:
        self._inner = inner
        self._reranker_name = reranker
        self._reranker = None

    @property
    def name(self) -> str:
        return f"{self._inner.name}+rerank_{self._reranker_name}"

    async def setup(self) -> None:
        await self._inner.setup()
        if self._reranker_name == "flashrank":
            self._reranker = _build_flashrank()
        elif self._reranker_name == "bge_reranker":
            self._reranker = _build_bge_reranker()

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        doc_type: str | None = None,
    ) -> list[RetrievalResult]:
        # Over-fetch from inner retriever
        candidates = await self._inner.retrieve(
            query=query, k=k * 3, doc_type=doc_type,
        )
        if not candidates:
            return []
        return self._rerank(query, candidates, k)

    def _rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        k: int,
    ) -> list[RetrievalResult]:
        """Score and re-sort candidates using the reranker."""
        texts = [c.document for c in candidates]
        scores = self._reranker.score(query, texts)
        paired = sorted(
            zip(candidates, scores), key=lambda x: x[1], reverse=True,
        )
        return [
            RetrievalResult(
                node_type=c.node_type,
                name=c.name,
                score=s,
                doc_type=c.doc_type,
                document=c.document,
            )
            for c, s in paired[:k]
        ]

    async def teardown(self) -> None:
        await self._inner.teardown()
        self._reranker = None


def _build_flashrank():
    """Lazy import FlashRank to avoid import errors if not installed."""
    from flashrank import Ranker
    return _FlashRankWrapper(Ranker(model_name="ms-marco-MiniLM-L-12-v2"))


def _build_bge_reranker():
    """Lazy import sentence-transformers CrossEncoder."""
    from sentence_transformers import CrossEncoder
    return _CrossEncoderWrapper(
        CrossEncoder("BAAI/bge-reranker-v2-m3", device="cpu"),
    )


class _FlashRankWrapper:
    def __init__(self, ranker) -> None:
        self._ranker = ranker

    def score(self, query: str, documents: list[str]) -> list[float]:
        from flashrank import RerankRequest
        passages = [{"text": d} for d in documents]
        request = RerankRequest(query=query, passages=passages)
        results = self._ranker.rerank(request)
        return [r["score"] for r in results]


class _CrossEncoderWrapper:
    def __init__(self, model) -> None:
        self._model = model

    def score(self, query: str, documents: list[str]) -> list[float]:
        pairs = [[query, doc] for doc in documents]
        scores = self._model.predict(pairs)
        return scores.tolist()
