"""LangChain tools for ARIA preflight agents — RAG node library search."""
from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

from src.boundary.chroma.store import ChromaStore
from src.services.rag.retrieval import hybrid_retrieve_n8n_nodes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton — connected once, reused across all tool calls
# ---------------------------------------------------------------------------
_store: ChromaStore | None = None


async def _get_store() -> ChromaStore:
    """Return the shared ChromaStore, connecting on first use."""
    global _store
    if _store is None:
        _store = ChromaStore()
        await _store.connect()
        logger.info("ChromaStore singleton connected (rag_tools)")
    return _store


@tool
async def search_n8n_nodes(query: str) -> str:
    """Search the n8n node library (500+ nodes) for a service or integration.

    Call ONLY for services NOT in the system prompt reference list.
    Returns the top 3 matches with exact node_type names you can use directly.
    Returns JSON: {"query": ..., "results": [{"node_type", "title", "description"}, ...]}.
    """
    try:
        store = await _get_store()
        raw = await hybrid_retrieve_n8n_nodes(store, query, n=5)
    except Exception as e:
        logger.error("search_n8n_nodes failed: %s", e)
        return json.dumps({"error": str(e)})

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
