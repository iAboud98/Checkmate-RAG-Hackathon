"""
Build the search index. This is the whole INDEXING phase in one script:

    PDFs --(load)--> pages --(chunk)--> chunks --(embed)--> vectors --(save)--> data/index/

Run it once, and again whenever the documents or the chunking/embedding settings change:
    python -m src.ingest.build_index
"""

import json
import time

from config import INDEX_DIR, RAW_DIR
from src.ingest.chunking import chunk_pages, embedding_text
from src.ingest.loaders import load_folder
from src.retrieval.embedder import embed_texts
from src.retrieval.store import VectorStore


def build_index(verbose: bool = True) -> int:
    start = time.time()
    log = print if verbose else (lambda *a, **k: None)

    metadata_file = RAW_DIR / "metadata.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.exists() else {}

    pages = load_folder(RAW_DIR)
    log(f"1. Loaded {len(pages)} pages from {len({p['source'] for p in pages})} PDFs")

    chunks = chunk_pages(pages, metadata)
    log(f"2. Split into {len(chunks)} chunks")

    vectors = embed_texts([embedding_text(c) for c in chunks])
    log(f"3. Embedded chunks -> vectors of shape {vectors.shape}")

    VectorStore(chunks, vectors).save(INDEX_DIR)
    log(f"4. Saved index to {INDEX_DIR}  ({time.time() - start:.1f}s)")
    return len(chunks)


if __name__ == "__main__":
    build_index()
