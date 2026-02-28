"""Build Cycle RAG Retriever — hybrid (BM25 + semantic) ChromaDB search."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.chroma.store import ChromaStore
from src.boundary.n8n.node_discovery import discover_installed_node_prefixes


async def rag_retriever_node(state: ARIAState) -> dict:
    """Query ChromaDB with hybrid search for n8n node templates.

    Uses hybrid_query_n8n_documents (BM25 + semantic RRF fusion) instead of
    pure semantic search so that exact node-type names like
    'n8n-nodes-base.slack' rank correctly alongside fuzzy intent matches.

    Retrieves up to 3 templates per required node type, deduplicated by
    document content, then appends a single combined query over the full
    intent string to surface relevant workflow-level context.
    """
    installed_prefixes = await discover_installed_node_prefixes()

    blueprint = state.get("build_blueprint") or {}
    intent: str = blueprint.get("intent") or state.get("intent", "")
    required_nodes: list[str] = blueprint.get("required_nodes") or state.get("required_nodes", [])

    store = ChromaStore()
    await store.connect()
    try:
        templates = await _retrieve_templates(store, intent, required_nodes)
    finally:
        await store.disconnect()

    return {
        "node_templates": templates,
        "available_node_packages": sorted(installed_prefixes),
        "status": "building",
        "messages": [HumanMessage(
            content=(
                f"[RAG] Retrieved {len(templates)} templates "
                f"for {len(required_nodes)} nodes via hybrid search."
            )
        )],
    }


async def _retrieve_templates(
    store: ChromaStore,
    intent: str,
    required_nodes: list[str],
) -> list[dict]:
    """Fetch per-node templates + intent-level context, deduplicated."""
    seen: set[str] = set()
    templates: list[dict] = []

    for node_type in required_nodes:
        results = await store.hybrid_query_n8n_documents(
            query=node_type, n_results=3, doc_type="node"
        )
        for doc in results:
            key = doc.get("document", "")
            if key not in seen:
                seen.add(key)
                templates.append(doc)

    if intent:
        context_results = await store.hybrid_query_n8n_documents(
            query=intent, n_results=5
        )
        for doc in context_results:
            key = doc.get("document", "")
            if key not in seen:
                seen.add(key)
                templates.append(doc)

    return templates
