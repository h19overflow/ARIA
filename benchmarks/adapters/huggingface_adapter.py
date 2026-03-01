"""
Retrieval adapter using local HuggingFace embedding models.
Builds a temporary in-memory Chroma collection with the alternate embeddings,
then queries it. Supports: BAAI/bge-m3, intfloat/e5-large-v2, thenlper/gte-large.
"""
from __future__ import annotations

import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from src.boundary.chroma.store import ChromaStore
from src.boundary.chroma._internals.bm25 import BM25Index
from src.boundary.chroma._internals.hybrid import hybrid_search
from benchmarks.adapters.base import BaseRetriever, RetrievalResult, add_documents_batched


class HuggingFaceRetriever(BaseRetriever):
    """Retriever using a local HuggingFace embedding model + hybrid search."""

    def __init__(self, model_name: str, search_mode: str = "hybrid") -> None:
        self._model_name = model_name
        self._search_mode = search_mode  # "semantic" or "hybrid"
        self._store: Chroma | None = None
        self._bm25: BM25Index | None = None
        self._docs: list[Document] = []

    @property
    def name(self) -> str:
        short = self._model_name.split("/")[-1]
        return f"hf_{short}_{self._search_mode}"

    async def setup(self) -> None:
        source = ChromaStore()
        await source.connect()
        raw = source._n8n_store.get(include=["documents", "metadatas"])
        self._docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(raw["documents"], raw["metadatas"])
        ]
        await source.disconnect()

        embeddings = HuggingFaceEmbeddings(
            model_name=self._model_name,
            model_kwargs={"device": "cpu"},
        )
        client = chromadb.Client()  # in-memory
        collection_name = f"bench_{self._model_name.replace('/', '_')}"
        self._store = Chroma(
            client=client,
            collection_name=collection_name,
            embedding_function=embeddings,
        )
        add_documents_batched(self._store, self._docs)

        if self._search_mode == "hybrid":
            self._bm25 = BM25Index(self._docs, k=20)

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        doc_type: str | None = None,
    ) -> list[RetrievalResult]:
        filter_ = {"doc_type": doc_type} if doc_type else None
        fetch_k = k * 4

        if self._search_mode == "semantic":
            pairs = self._store.similarity_search_with_relevance_scores(
                query, k=k, filter=filter_,
            )
            return [_pair_to_result(doc, score) for doc, score in pairs]

        semantic = self._store.similarity_search_with_relevance_scores(
            query, k=fetch_k, filter=filter_,
        )
        fused = hybrid_search(
            query, self._bm25, semantic, k=k, fetch_k=fetch_k,
        )
        return [_dict_to_result(r) for r in fused]

    async def teardown(self) -> None:
        self._store = None
        self._bm25 = None
        self._docs = []



def _pair_to_result(doc: Document, score: float) -> RetrievalResult:
    return RetrievalResult(
        node_type=doc.metadata.get("node_type", ""),
        name=doc.metadata.get("name", ""),
        score=score,
        doc_type=doc.metadata.get("doc_type", ""),
        document=doc.page_content,
    )


def _dict_to_result(raw: dict) -> RetrievalResult:
    return RetrievalResult(
        node_type=raw.get("node_type", ""),
        name=raw.get("name", ""),
        score=raw.get("score", 0.0),
        doc_type=raw.get("doc_type", ""),
        document=raw.get("document", ""),
    )
