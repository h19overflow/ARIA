"""
Convert N8nDocument and ApiEndpoint into LangChain Document objects
ready for upsert into the Chroma vector store.
"""

from langchain_core.documents import Document

from src.boundary.scraper._internals.normalizer import N8nDocument
from src.boundary.scraper.api_parser import ApiEndpoint


def n8n_doc_to_langchain(doc: N8nDocument) -> tuple[Document, str]:
    return (
        Document(
            page_content=doc.text,
            metadata={
                "name": doc.name,
                "doc_type": doc.doc_type,
                "description": doc.description,
                **doc.metadata,
            },
        ),
        doc.id,
    )


def api_endpoint_to_langchain(endpoint: ApiEndpoint) -> tuple[Document, str]:
    return (
        Document(
            page_content=endpoint.text,
            metadata=endpoint.metadata,
        ),
        endpoint.id,
    )
