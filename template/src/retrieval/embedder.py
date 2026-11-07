"""
Embeddings, i.e. turning text into vectors of numbers.

An embedding model reads a piece of text and outputs a list of numbers
(3072 of them for text-embedding-3-large) that captures its MEANING.
Texts with similar meaning get vectors pointing in a similar direction,
even when they share no words:

    "كم الحد المسموح للغياب؟"      and      "لا يجوز أن تتجاوز نسبة غياب الطالب 20%"
        -> vectors are close (cosine similarity high)

That's what lets us find the right chunk for a question phrased differently
from the document, or even in another dialect/language.
"""

import numpy as np

from config import EMBEDDING_MODEL
from src.openai_client import get_client

BATCH_SIZE = 100  # the API accepts many texts per call; batching = fewer, faster requests


def embed_texts(texts: list[str]) -> np.ndarray:
    client = get_client()
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts[i:i + BATCH_SIZE])
        vectors.extend(item.embedding for item in response.data)
    return normalize_rows(np.array(vectors, dtype=np.float32))


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Scale every vector to length 1, so a plain dot product = cosine similarity."""
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)
