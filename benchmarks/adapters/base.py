from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


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
