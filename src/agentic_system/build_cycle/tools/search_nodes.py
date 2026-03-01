"""LangChain tool — on-demand ChromaDB search for n8n node templates."""
from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.agentic_system.build_cycle.schemas.node_plan import SearchInput
from src.boundary.chroma.store import ChromaStore

logger = logging.getLogger(__name__)



@tool(args_schema=SearchInput)
async def search_n8n_nodes(
    query: str,
    doc_type: str | None = "node",
    n_results: int = 5,
) -> str:
    """Search the n8n knowledge base for node documentation and parameter templates.

    Use this tool BEFORE selecting any node type to verify it exists and
    understand its parameter schema. Adjust n_results for broad queries (up to 20).
    """
    store = ChromaStore()
    await store.connect()
    try:
        results = await store.query_n8n_documents(
            query=query, n_results=n_results, doc_type=doc_type,
        )
    finally:
        await store.disconnect()

    if not results:
        return f"No results found for query: '{query}'"

    formatted = _format_results(results)
    logger.info("[SearchTool] query=%r → %d results", query, len(results))
    return formatted


def _format_results(results: list[dict]) -> str:
    """Format ChromaDB results into a readable string for the LLM."""
    entries: list[str] = []
    for i, doc in enumerate(results, 1):
        node_type = doc.get("node_type") or doc.get("name") or "unknown"
        text = doc.get("document", "")
        score = doc.get("score", 0)
        entries.append(f"### Result {i} — {node_type} (score: {score:.3f})\n{text}")
    return "\n\n".join(entries)
