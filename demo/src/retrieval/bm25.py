"""
MILESTONE 5a: BM25, classic keyword search.

Embeddings understand meaning but can be fuzzy with exact tokens: course codes
(CPE310), numbers, names, rare terms. BM25 is the opposite: it only matches
words, but it matches them exactly. It scores a chunk higher when:
  * it contains the question's words,
  * those words are RARE across all chunks (a match on "CPE310" counts far
    more than a match on "الطالب", which is everywhere),
  * the chunk is short (a match in a short chunk is more focused).

It runs on the normalized tokens from normalize.tokenize(), so "الإنذار" and
"الانذار" match.
"""

from rank_bm25 import BM25Okapi

from src.ingest.normalize import tokenize


class BM25Index:
    def __init__(self, chunks: list[dict]):
        corpus = [tokenize(f"{c['title']} {c['text']}") for c in chunks]
        self.bm25 = BM25Okapi(corpus)

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        """Return [(chunk_index, bm25_score), ...] best first, skipping zero scores."""
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [(i, float(scores[i])) for i in ranked if scores[i] > 0]
