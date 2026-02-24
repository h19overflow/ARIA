"""LangChain tools for ARIA preflight agents — RAG node library search."""
from __future__ import annotations

import json

from langchain_core.tools import tool

from src.boundary.chroma.store import ChromaStore
from src.services.retrieval_service import hybrid_retrieve_n8n_nodes


@tool
async def search_n8n_nodes(query: str) -> str:
    """Search the n8n node library (500+ nodes) using semantic + keyword hybrid search.

    Use this when you need to find the exact n8n node type name for a service or action
    the user mentioned, or when you are unsure whether a node exists for a given integration.
    Returns the top 5 matching nodes with their type name and description.
    Returns JSON: {"query": ..., "results": [{"node_type", "title", "description", "doc_type"}, ...]}.
    """
    store = ChromaStore()
    await store.connect()
    try:
        raw = await hybrid_retrieve_n8n_nodes(store, query, n=5)
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
