"""
MILESTONE 4b: The vector store, i.e. where vectors live and how we search them.

Real projects use a vector database (FAISS, Chroma, pgvector, Qdrant...). Under
the hood they all do what these ~30 lines do: keep one vector per chunk and,
for a question vector, find the chunks whose vectors are most similar.

With vectors normalized to length 1, similarity is one matrix multiplication:
    scores = all_chunk_vectors @ question_vector      (one score per chunk, -1..1)

This brute-force search is instant for thousands of chunks. For millions you'd
switch to a vector database that uses approximate search (HNSW indexes).
"""

import json
from pathlib import Path

import numpy as np


class VectorStore:
    def __init__(self, chunks: list[dict], vectors: np.ndarray):
        self.chunks = chunks      # chunk i's text + metadata ...
        self.vectors = vectors    # ... matches row i of this matrix

    def search(self, query_vector: np.ndarray, k: int) -> list[tuple[int, float]]:
        """Return [(chunk_index, cosine_score), ...] best first."""
        scores = self.vectors @ query_vector
        best = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in best]

    # --- persistence: so we embed once, not on every app start ---------------
    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / "embeddings.npy", self.vectors)
        with open(folder / "chunks.jsonl", "w", encoding="utf-8") as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, folder: Path) -> "VectorStore":
        if not (folder / "embeddings.npy").exists():
            raise FileNotFoundError("No index found. Run:  python -m src.ingest.build_index")
        vectors = np.load(folder / "embeddings.npy")
        with open(folder / "chunks.jsonl", encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f]
        return cls(chunks, vectors)
