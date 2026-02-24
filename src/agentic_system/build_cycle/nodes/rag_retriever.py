"""Build Cycle RAG Retriever — queries ChromaDB for node templates."""
from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.agentic_system.shared.state import ARIAState
from src.boundary.chroma.store import ChromaStore


async def rag_retriever_node(state: ARIAState) -> dict:
    """Query ChromaDB for n8n node templates matching required_nodes."""
    required_nodes = state["required_nodes"]

    store = ChromaStore()
    await store.connect()
    try:
        templates = []
        for node_type in required_nodes:
            results = await store.query_n8n_documents(
                query=node_type, n_results=1, doc_type="node"
            )
            if results:
                templates.append(results[0])
    finally:
        await store.disconnect()

    return {
        "node_templates": templates,
        "status": "building",
        "messages": [HumanMessage(
            content=f"[RAG] Retrieved {len(templates)} templates for {len(required_nodes)} nodes."
        )],
    }
