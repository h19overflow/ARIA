"""
Retrieval adapter that re-chunks documents before embedding.
Strategies: fixed_512 (512 tokens, 64 overlap), parent_child (full + 256 chunks).
"""
from __future__ import annotations

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.api.settings import settings
from src.boundary.chroma.store import ChromaStore
from src.boundary.chroma._internals.bm25 import BM25Index
from src.boundary.chroma._internals.hybrid import hybrid_search
from benchmarks.adapters.base import BaseRetriever, RetrievalResult, add_documents_batched


class ChunkedRetriever(BaseRetriever):
    """Re-chunks n8n docs before embedding for benchmark comparison."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        strategy: str = "fixed",  # "fixed" or "parent_child"
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._strategy = strategy
        self._store: Chroma | None = None
        self._bm25: BM25Index | None = None

    @property
    def name(self) -> str:
        if self._strategy == "parent_child":
            return "chunked_parent_child"
        return f"chunked_{self._chunk_size}"

    async def setup(self) -> None:
        source = ChromaStore()
        await source.connect()
        raw = source._n8n_store.get(include=["documents", "metadatas"])
        original_docs = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(raw["documents"], raw["metadatas"])
        ]
        await source.disconnect()

        chunks = self._split_documents(original_docs)

        embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.google_api_key,
        )
        client = chromadb.Client()
        self._store = Chroma(
            client=client,
            collection_name=f"bench_chunked_{self._strategy}",
            embedding_function=embeddings,
        )
        add_documents_batched(self._store, chunks)
        self._bm25 = BM25Index(chunks, k=20)

    def _split_documents(self, docs: list[Document]) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        if self._strategy == "fixed":
            return splitter.split_documents(docs)

        # parent_child: keep original + add small chunks
        small_splitter = RecursiveCharacterTextSplitter(
            chunk_size=256, chunk_overlap=32,
        )
        children = small_splitter.split_documents(docs)
        return docs + children  # both parent and child in collection

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        doc_type: str | None = None,
    ) -> list[RetrievalResult]:
        filter_ = {"doc_type": doc_type} if doc_type else None
        fetch_k = k * 4
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



def _dict_to_result(raw: dict) -> RetrievalResult:
    return RetrievalResult(
        node_type=raw.get("node_type", ""),
        name=raw.get("name", ""),
        score=raw.get("score", 0.0),
        doc_type=raw.get("doc_type", ""),
        document=raw.get("document", ""),
    )
