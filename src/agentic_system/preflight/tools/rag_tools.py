"""LangChain tools for ARIA preflight agents — RAG node library search."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from src.boundary.chroma.store import ChromaStore
from src.services.rag.retrieval import hybrid_retrieve_n8n_nodes


@tool
async def search_n8n_nodes(query: str) -> str:
    """Search the n8n node library (500+ nodes) for a service or integration.

    Call ONLY for services NOT in the system prompt reference list.
    Returns the top 3 matches with exact node_type names you can use directly.
    Returns JSON: {"query": ..., "results": [{"node_type", "title", "description"}, ...]}.
    """
    store = ChromaStore()
    await store.connect()
    try:
        raw = await hybrid_retrieve_n8n_nodes(store, query, n=3)
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        await store.disconnect()

    results = [_map_result(r) for r in raw]
    return json.dumps({"query": query, "results": results})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _map_result(r: dict) -> dict:
    """Extract display fields from a raw retrieval result dict."""
    meta = r.get("metadata") or {}
    page_content: str = r.get("page_content", "")
    description = meta.get("description") or page_content[:150]
    return {
        "node_type": meta.get("node_type") or meta.get("type", ""),
        "title": meta.get("title") or meta.get("name", ""),
        "description": description,
        "doc_type": meta.get("doc_type", ""),
    }
