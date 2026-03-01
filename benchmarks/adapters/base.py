from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_core.documents import Document

_CHROMA_BATCH_SIZE = 5000


@dataclass
class RetrievalResult:
    """Single retrieval result with identity and score."""
    node_type: str      # e.g. "n8n-nodes-base.slack"
    name: str           # human-readable name
    score: float        # relevance score (higher = better)
    doc_type: str       # "node" or "workflow_template"
    document: str       # raw page_content


class BaseRetriever(ABC):
    """Abstract retriever — all benchmark adapters implement this."""

    @abstractmethod
    async def setup(self) -> None:
        """Initialize connections, load models, build indexes."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        k: int = 5,
        doc_type: str | None = None,
    ) -> list[RetrievalResult]:
        """Run retrieval and return ranked results."""

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up resources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for reports."""


def add_documents_batched(store: Chroma, docs: list[Document]) -> None:
    """Add documents in batches to avoid Chroma max batch size errors."""
    for start in range(0, len(docs), _CHROMA_BATCH_SIZE):
        batch = docs[start:start + _CHROMA_BATCH_SIZE]
        store.add_documents(batch)
