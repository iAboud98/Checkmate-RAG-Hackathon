"""
Build the search index from every document in DOCS_DIR:

    files --(load)--> blocks --(sections)--> chunks --(embed)--> vectors --(save)--> data/index/

    python -m src.ingest.build_index
Run scripts/check_extraction.py first to see the sections before paying for embeddings.
"""

import time

from config import DOCS_DIR, INDEX_DIR
from src.ingest.loaders import list_documents, load_blocks, load_metadata
from src.ingest.sections import build_sections, embedding_text, sections_to_chunks
from src.retrieval.embedder import embed_texts
from src.retrieval.store import VectorStore


def build_index(verbose: bool = True) -> int:
    start = time.time()
    log = print if verbose else (lambda *a, **k: None)
    metadata = load_metadata(DOCS_DIR)
    chunks = []
    for path in list_documents(DOCS_DIR):
        meta = metadata.get(path.name, {})
        sections = build_sections(load_blocks(path, meta), meta.get("title", path.stem))
        doc_chunks = sections_to_chunks(sections, path.name, meta)
        log(f"  {path.name}: {len(sections)} sections -> {len(doc_chunks)} chunks")
        chunks.extend(doc_chunks)
    if not chunks:
        raise RuntimeError(f"No content found in {DOCS_DIR}")
    for i, c in enumerate(chunks):
        c["id"] = f"{c['id']}#{i}"   # globally unique
    vectors = embed_texts([embedding_text(c) for c in chunks])
    VectorStore(chunks, vectors).save(INDEX_DIR)
    log(f"Indexed {len(chunks)} chunks from {DOCS_DIR} in {time.time() - start:.1f}s")
    return len(chunks)


if __name__ == "__main__":
    build_index()
