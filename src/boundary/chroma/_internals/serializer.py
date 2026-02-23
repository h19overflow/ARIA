"""
Convert N8nDocument and ApiEndpoint dataclasses into the flat dicts
that ChromaDB's upsert API expects.
"""

from src.boundary.scraper._internals.normalizer import N8nDocument
from src.boundary.scraper.api_parser import ApiEndpoint


def n8n_doc_to_chroma(doc: N8nDocument) -> dict:
    return {
        "id": doc.id,
        "document": doc.text,
        "metadata": {
            "name": doc.name,
            "doc_type": doc.doc_type,
            "description": doc.description,
            **doc.metadata,
        },
    }


def api_endpoint_to_chroma(endpoint: ApiEndpoint) -> dict:
    return {
        "id": endpoint.id,
        "document": endpoint.text,
        "metadata": endpoint.metadata,
    }
