"""
Retrieval use cases.
Semantic search over n8n documents and user API endpoint specs.
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
