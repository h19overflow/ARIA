"""
ChromaDB vector store via langchain-chroma.
Uses Google Generative AI embeddings for all collections.
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.api.settings import settings
from src.boundary.chroma._internals.bm25 import BM25Index
from src.boundary.chroma._internals.hybrid import hybrid_search
from src.boundary.chroma._internals.serializer import n8n_doc_to_langchain, api_endpoint_to_langchain
from src.boundary.scraper._internals.normalizer import N8nDocument
from src.boundary.scraper.api_parser import ApiEndpoint

N8N_COLLECTION = "n8n_documents"
API_SPEC_COLLECTION = "api_specs"

# BM25 fetch multiplier — retrieve more candidates before RRF fusion
_FETCH_MULTIPLIER = 4


class ChromaStore:
    def __init__(self) -> None:
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.google_api_key,
        )
        self._n8n_store: Chroma | None = None
        self._api_store: Chroma | None = None
        # BM25 indexes built lazily on first hybrid query
        self._n8n_bm25: BM25Index | None = None
        self._api_bm25: BM25Index | None = None

    async def connect(self) -> None:
        self._n8n_store = Chroma(
            collection_name=N8N_COLLECTION,
            embedding_function=self._embeddings,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        self._api_store = Chroma(
            collection_name=API_SPEC_COLLECTION,
            embedding_function=self._embeddings,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )

    async def disconnect(self) -> None:
        self._n8n_store = None
        self._api_store = None
        self._n8n_bm25 = None
        self._api_bm25 = None

    # ------------------------------------------------------------------
    # n8n documents (nodes + workflow templates)
    # ------------------------------------------------------------------

    def upsert_n8n_documents(self, documents: list[N8nDocument]) -> None:
        pairs = {doc.id: n8n_doc_to_langchain(doc) for doc in documents}  # dedup by id
        docs, ids = zip(*pairs.values())
        self._n8n_store.add_documents(documents=list(docs), ids=list(ids))
        self._n8n_bm25 = None  # invalidate index after upsert

    async def query_n8n_documents(
        self,
        query: str,
        n_results: int = 5,
        doc_type: str | None = None,
    ) -> list[dict]:
        filter_ = {"doc_type": doc_type} if doc_type else None
        results = self._n8n_store.similarity_search_with_relevance_scores(
            query, k=n_results, filter=filter_
        )
        return [_doc_to_dict(doc, score) for doc, score in results]

    async def hybrid_query_n8n_documents(
        self,
        query: str,
        n_results: int = 5,
        doc_type: str | None = None,
        alpha: float | None = None,
    ) -> list[dict]:
        filter_ = {"doc_type": doc_type} if doc_type else None
        fetch_k = n_results * _FETCH_MULTIPLIER

        semantic = self._n8n_store.similarity_search_with_relevance_scores(
            query, k=fetch_k, filter=filter_
        )
        bm25 = self._get_n8n_bm25(doc_type)
        return hybrid_search(query, bm25, semantic, k=n_results, fetch_k=fetch_k, alpha=alpha)

    def _get_n8n_bm25(self, doc_type: str | None) -> BM25Index:
        """Build (or return cached) BM25 index for the n8n collection."""
        if self._n8n_bm25 is None:
            all_docs = self._n8n_store.get(include=["documents", "metadatas"])
            docs = [
                Document(page_content=text, metadata=meta)
                for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
            ]
            self._n8n_bm25 = BM25Index(docs, k=20)

        if doc_type is None:
            return self._n8n_bm25

        # Filter in-memory for doc_type — BM25Index wraps the filtered subset
        all_docs = self._n8n_store.get(include=["documents", "metadatas"])
        filtered = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
            if meta.get("doc_type") == doc_type
        ]
        return BM25Index(filtered, k=20)

    # ------------------------------------------------------------------
    # User API spec endpoints
    # ------------------------------------------------------------------

    def upsert_api_endpoints(self, endpoints: list[ApiEndpoint]) -> None:
        pairs = {e.id: api_endpoint_to_langchain(e) for e in endpoints}  # dedup by id
        docs, ids = zip(*pairs.values())
        self._api_store.add_documents(documents=list(docs), ids=list(ids))
        self._api_bm25 = None  # invalidate index after upsert

    async def query_api_endpoints(
        self,
        query: str,
        n_results: int = 5,
        source: str | None = None,
    ) -> list[dict]:
        filter_ = {"source": source} if source else None
        results = self._api_store.similarity_search_with_relevance_scores(
            query, k=n_results, filter=filter_
        )
        return [_doc_to_dict(doc, score) for doc, score in results]

    async def hybrid_query_api_endpoints(
        self,
        query: str,
        n_results: int = 5,
        source: str | None = None,
        alpha: float | None = None,
    ) -> list[dict]:
        filter_ = {"source": source} if source else None
        fetch_k = n_results * _FETCH_MULTIPLIER

        semantic = self._api_store.similarity_search_with_relevance_scores(
            query, k=fetch_k, filter=filter_
        )
        if self._api_bm25 is None:
            all_docs = self._api_store.get(include=["documents", "metadatas"])
            docs = [
                Document(page_content=text, metadata=meta)
                for text, meta in zip(all_docs["documents"], all_docs["metadatas"])
            ]
            self._api_bm25 = BM25Index(docs, k=20)

        return hybrid_search(query, self._api_bm25, semantic, k=n_results, fetch_k=fetch_k, alpha=alpha)


def _doc_to_dict(doc: Document, score: float) -> dict:
    return {"document": doc.page_content, "score": round(score, 4), **doc.metadata}
