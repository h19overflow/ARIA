"""
Retrieval use cases.
Semantic and hybrid search over n8n documents and user API endpoint specs.
"""

from src.boundary.chroma.store import ChromaStore


async def retrieve_n8n_nodes(
    store: ChromaStore,
    query: str,
    n: int = 5,
) -> list[dict]:
    """Semantic search over n8n node documents only."""
    return await store.query_n8n_documents(query, n_results=n, doc_type="node")


async def retrieve_workflow_templates(
    store: ChromaStore,
    query: str,
    n: int = 5,
) -> list[dict]:
    """Semantic search over n8n workflow template documents only."""
    return await store.query_n8n_documents(query, n_results=n, doc_type="workflow_template")


async def retrieve_api_endpoints(
    store: ChromaStore,
    query: str,
    n: int = 5,
    source: str | None = None,
) -> list[dict]:
    """Semantic search over user API endpoint specs."""
    return await store.query_api_endpoints(query, n_results=n, source=source)


# ---------------------------------------------------------------------------
# Hybrid variants (BM25 + semantic, RRF fusion)
# ---------------------------------------------------------------------------

async def hybrid_retrieve_n8n_nodes(
    store: ChromaStore,
    query: str,
    n: int = 5,
    alpha: float | None = None,
) -> list[dict]:
    """Hybrid search (BM25 + semantic, RRF) over n8n node documents."""
    return await store.hybrid_query_n8n_documents(
        query, n_results=n, doc_type="node", alpha=alpha
    )


async def hybrid_retrieve_workflow_templates(
    store: ChromaStore,
    query: str,
    n: int = 5,
    alpha: float | None = None,
) -> list[dict]:
    """Hybrid search (BM25 + semantic, RRF) over workflow template documents."""
    return await store.hybrid_query_n8n_documents(
        query, n_results=n, doc_type="workflow_template", alpha=alpha
    )


async def hybrid_retrieve_api_endpoints(
    store: ChromaStore,
    query: str,
    n: int = 5,
    source: str | None = None,
    alpha: float | None = None,
) -> list[dict]:
    """Hybrid search (BM25 + semantic, RRF) over user API endpoint specs."""
    return await store.hybrid_query_api_endpoints(
        query, n_results=n, source=source, alpha=alpha
    )
