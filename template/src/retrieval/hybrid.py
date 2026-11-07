"""
Hybrid search, combining meaning (vectors) and keywords (BM25).

Each method returns its own ranked list, and their scores live on different
scales (cosine 0..1 vs BM25 0..20+), so we can't simply add them.

Reciprocal Rank Fusion (RRF) ignores the scores and uses only the RANK:
    rrf_score(chunk) = sum over methods of  1 / (RRF_K + rank_in_that_method)

A chunk ranked #1 by both methods wins. A chunk ranked #1 by one method and
missing from the other still scores well. RRF_K=60 is the standard value
from the original paper; it stops the very top rank from dominating.
"""

from dataclasses import dataclass

from config import CANDIDATES, RRF_K, TOP_K
from src.retrieval.bm25 import BM25Index
from src.retrieval.embedder import embed_query
from src.retrieval.store import VectorStore


@dataclass
class RetrievalResult:
    chunks: list[dict]        # the top_k chunks, best first, each with its scores attached
    best_dense_score: float   # highest cosine similarity of any chunk (used to decide refusal)


class HybridRetriever:
    def __init__(self, store: VectorStore):
        self.store = store
        self.bm25 = BM25Index(store.chunks)

    def retrieve(self, query: str, top_k: int = TOP_K, use_bm25: bool = True) -> RetrievalResult:
        dense = self.store.search(embed_query(query), CANDIDATES)
        sparse = self.bm25.search(query, CANDIDATES) if use_bm25 else []

        fused: dict[int, float] = {}
        for ranked_list in (dense, sparse):
            for rank, (idx, _score) in enumerate(ranked_list, start=1):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank)

        dense_scores = dict(dense)
        bm25_scores = dict(sparse)
        best = sorted(fused, key=lambda i: -fused[i])[:top_k]

        chunks = []
        for idx in best:
            chunk = dict(self.store.chunks[idx])
            chunk["scores"] = {
                "rrf": round(fused[idx], 4),
                "cosine": round(dense_scores.get(idx, 0.0), 3),
                "bm25": round(bm25_scores.get(idx, 0.0), 2),
            }
            chunks.append(chunk)

        best_dense = dense[0][1] if dense else 0.0
        return RetrievalResult(chunks=chunks, best_dense_score=best_dense)
