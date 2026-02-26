"""Services barrel — lazy re-exports to avoid circular imports."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """Lazily resolve backward-compat re-exports on first access."""
    _pipeline_names = {"run_build"}
    _rag_ingestion_names = {
        "ingest_n8n_nodes", "ingest_n8n_workflow_templates", "ingest_api_spec",
    }
    _rag_retrieval_names = {
        "retrieve_n8n_nodes", "retrieve_workflow_templates", "retrieve_api_endpoints",
        "hybrid_retrieve_n8n_nodes", "hybrid_retrieve_workflow_templates",
        "hybrid_retrieve_api_endpoints",
    }

    if name in _pipeline_names:
        from src.services.pipeline import build as _build
        return getattr(_build, name)

    if name in _rag_ingestion_names:
        from src.services.rag import ingestion as _ing
        return getattr(_ing, name)

    if name in _rag_retrieval_names:
        from src.services.rag import retrieval as _ret
        return getattr(_ret, name)

    raise AttributeError(f"module 'src.services' has no attribute {name!r}")
