"""
RRF (Reciprocal Rank Fusion) hybrid search.

Combines BM25 keyword results and semantic vector results into a single
ranked list. Alpha controls the semantic weight:
  0.0 = pure BM25 | 0.5 = balanced | 1.0 = pure semantic
"""

from langchain_core.documents import Document

from src.boundary.chroma._internals.bm25 import BM25Index

# n8n domain: node type IDs (e.g. "n8n-nodes-base.slack") and operation names
# benefit from keyword matching → default alpha balanced at 0.5
DEFAULT_ALPHA = 0.5
RRF_K = 60  # standard RRF constant


def _doc_key(doc: Document) -> str:
    """Stable identity key for a document — prefers metadata name over content hash."""
    return doc.metadata.get("name") or doc.page_content[:80]


_N8N_NODE_PREFIXES = ("n8n-nodes-base.", "n8n-nodes-langchain.", "@n8n/")


def _detect_alpha(query: str) -> float:
    """
    Shift alpha toward keyword search when the query looks technical.
    Node type IDs (n8n-nodes-base.slack) go pure semantic — BM25 tokenization
    on hyphen/dot notation produces noise.
    """
    # Exact node type ID — embeddings handle this better than BM25
    if any(query.strip().startswith(p) for p in _N8N_NODE_PREFIXES):
        return 1.0

    signals = [
        '"' in query,                                               # quoted exact term
        any(t.isupper() and len(t) > 1 for t in query.split()),   # acronym
        any(c.isdigit() for c in query),                           # version/ID number
        len(query.split()) <= 3,                                   # very short / terse
    ]
    hit = sum(signals)
    if hit >= 2:
        return 0.3   # keyword heavy
    if hit == 1:
        return 0.5   # balanced
    return 0.7       # natural language → semantic heavy


def rrf_fuse(
    bm25_docs: list[Document],
    semantic_pairs: list[tuple[Document, float]],
    alpha: float,
    k: int,
) -> list[dict]:
    """
    Fuse BM25 and semantic results via RRF, return top-k as result dicts.

    Each result dict contains: document, score (RRF), semantic_score,
    bm25_rank, and all metadata fields.
    """
    semantic_docs = [doc for doc, _ in semantic_pairs]
    sem_score_map: dict[str, float] = {
        _doc_key(doc): score for doc, score in semantic_pairs
    }

    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for rank, doc in enumerate(bm25_docs):
        key = _doc_key(doc)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + (1 - alpha) / (RRF_K + rank + 1)
        doc_map[key] = doc

    for rank, doc in enumerate(semantic_docs):
        key = _doc_key(doc)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + alpha / (RRF_K + rank + 1)
        doc_map[key] = doc

    ranked = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:k]

    results = []
    for key in ranked:
        doc = doc_map[key]
        results.append({
            "document": doc.page_content,
            "score": round(rrf_scores[key], 6),
            "semantic_score": round(sem_score_map.get(key, 0.0), 4),
            "bm25_matched": key in {_doc_key(d) for d in bm25_docs},
            **doc.metadata,
        })
    return results


def hybrid_search(
    query: str,
    bm25_index: BM25Index,
    semantic_results: list[tuple[Document, float]],
    k: int = 5,
    fetch_k: int = 20,
    alpha: float | None = None,
) -> list[dict]:
    """
    Run hybrid search and return fused results.
    If alpha is None, it is inferred dynamically from the query.
    """
    effective_alpha = alpha if alpha is not None else _detect_alpha(query)
    bm25_docs = bm25_index.retrieve(query, k=fetch_k)
    return rrf_fuse(bm25_docs, semantic_results, alpha=effective_alpha, k=k)
