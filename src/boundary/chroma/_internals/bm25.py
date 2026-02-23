"""
In-memory BM25 keyword retriever built from a list of LangChain Documents.
Wraps langchain-community BM25Retriever with a domain-aware tokenizer that
preserves n8n node type identifiers (e.g. n8n-nodes-base.slack) as single tokens.
"""

import re

from langchain_community.retrievers import BM25Retriever as _LCBm25
from langchain_core.documents import Document

# Splits on whitespace and common punctuation but keeps hyphen-dot compounds intact
_TOKEN_RE = re.compile(r"[^\w.\-]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase + split, preserving node-type compound tokens."""
    return [t for t in _TOKEN_RE.split(text.lower()) if t]


class BM25Index:
    """Thin wrapper: build once from a document list, query many times."""

    def __init__(self, documents: list[Document], k: int = 20) -> None:
        self._k = k
        self._retriever = _LCBm25.from_documents(
            documents, k=k, preprocess_func=_tokenize
        )

    def retrieve(self, query: str, k: int | None = None) -> list[Document]:
        self._retriever.k = k or self._k
        return self._retriever.invoke(query)
