"""
ChromaDB client wrapper.
Owns collection management, upsert, and semantic query for both
n8n documents and user API endpoint specs.
"""

import chromadb
from chromadb import AsyncHttpClient

from src.api.settings import settings
from src.boundary.chroma._internals.serializer import n8n_doc_to_chroma, api_endpoint_to_chroma
from src.boundary.scraper._internals.normalizer import N8nDocument
from src.boundary.scraper.api_parser import ApiEndpoint

N8N_COLLECTION = "n8n_documents"
API_SPEC_COLLECTION = "api_specs"


class ChromaStore:
    def __init__(self) -> None:
        self._client: AsyncHttpClient | None = None

    async def connect(self) -> None:
        self._client = await chromadb.AsyncHttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )

    async def disconnect(self) -> None:
        self._client = None

    # ------------------------------------------------------------------
    # n8n documents (nodes + workflow templates)
    # ------------------------------------------------------------------

    async def upsert_n8n_documents(self, documents: list[N8nDocument]) -> None:
        collection = await self._client.get_or_create_collection(N8N_COLLECTION)
        records = [n8n_doc_to_chroma(d) for d in documents]
        await collection.upsert(
            ids=[r["id"] for r in records],
            documents=[r["document"] for r in records],
            metadatas=[r["metadata"] for r in records],
        )

    async def query_n8n_documents(
        self,
        query: str,
        n_results: int = 5,
        doc_type: str | None = None,
    ) -> list[dict]:
        collection = await self._client.get_or_create_collection(N8N_COLLECTION)
        where = {"doc_type": doc_type} if doc_type else None
        results = await collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        return _flatten_results(results)

    # ------------------------------------------------------------------
    # User API spec endpoints
    # ------------------------------------------------------------------

    async def upsert_api_endpoints(self, endpoints: list[ApiEndpoint]) -> None:
        collection = await self._client.get_or_create_collection(API_SPEC_COLLECTION)
        records = [api_endpoint_to_chroma(e) for e in endpoints]
        await collection.upsert(
            ids=[r["id"] for r in records],
            documents=[r["document"] for r in records],
            metadatas=[r["metadata"] for r in records],
        )

    async def query_api_endpoints(
        self,
        query: str,
        n_results: int = 5,
        source: str | None = None,
    ) -> list[dict]:
        collection = await self._client.get_or_create_collection(API_SPEC_COLLECTION)
        where = {"source": source} if source else None
        results = await collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        return _flatten_results(results)


def _flatten_results(results: dict) -> list[dict]:
    """Zip ChromaDB result arrays into a list of dicts."""
    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]
    ids = results.get("ids", [[]])[0]
    return [
        {"id": i, "document": d, **m}
        for i, d, m in zip(ids, documents, metadatas)
    ]
