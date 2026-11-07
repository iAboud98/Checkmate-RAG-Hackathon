"""
MILESTONE 3: Chunking, i.e. cutting pages into small pieces we can search.

Why not search whole documents? Two reasons:
  * Precision: a question about fees should retrieve the 3 lines about fees,
    not a 10-page document where fees are mentioned once.
  * Cost and focus: we send the retrieved text to the LLM. Smaller, relevant
    pieces = cheaper calls and fewer distractions for the model.

Our strategy (simple and explainable):
  * Never cross a page boundary, so every chunk has exactly one page number.
  * Pack whole lines into a chunk until it reaches CHUNK_SIZE characters.
    (We never cut in the middle of a line, so table rows stay intact.)
  * Start the next chunk with the last ~CHUNK_OVERLAP characters of the
    previous one, so a sentence that sits on the border appears in both.
  * Attach metadata to every chunk: source file, page, title, version, date.
"""

from config import CHUNK_OVERLAP, CHUNK_SIZE


def chunk_pages(pages: list[dict], metadata: dict) -> list[dict]:
    chunks = []
    for page in pages:
        doc_meta = metadata.get(page["source"], {})
        for text in split_text(page["text"], CHUNK_SIZE, CHUNK_OVERLAP):
            chunks.append({
                "id": f"{page['source']}#p{page['page']}#c{len(chunks)}",
                "text": text,
                "source": page["source"],
                "page": page["page"],
                "title": doc_meta.get("title", page["source"]),
                "version": doc_meta.get("version", ""),
                "date": doc_meta.get("date", ""),
            })
    return chunks


def split_text(text: str, size: int, overlap: int) -> list[str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    chunks, current = [], []

    for line in lines:
        if current and len("\n".join(current + [line])) > size:
            chunks.append("\n".join(current))
            current = _tail(current, overlap)   # carry the overlap into the next chunk
        current.append(line)

    if current:
        chunks.append("\n".join(current))
    return chunks


def _tail(lines: list[str], overlap: int) -> list[str]:
    """Return the last lines whose total length fits in `overlap` characters."""
    tail, total = [], 0
    for line in reversed(lines):
        if total + len(line) > overlap:
            break
        tail.insert(0, line)
        total += len(line)
    return tail


def embedding_text(chunk: dict) -> str:
    """
    The text we actually embed: the chunk plus a short header with the document
    title and version. A chunk that only says "الحد الأقصى 18 ساعة" becomes much
    easier to find once the vector also "knows" it comes from the 2025 regulations.
    """
    header = f"{chunk['title']} - إصدار {chunk['version']}" if chunk["version"] else chunk["title"]
    return f"{header}\n{chunk['text']}"
