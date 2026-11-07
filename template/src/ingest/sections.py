"""
SECTION-BASED CHUNKING: one chunk = one section of the document.

Why sections instead of fixed-size or per-page chunks?
  * A section is a unit of MEANING the author already defined: "المادة 5: الإجازة المرضية"
    talks about one thing. Fixed-size chunks cut rules in half, and page chunks mix topics.
  * The section title is a free, human-written summary of its content. We embed it with
    the text, and we cite it: [hr_policies.pdf، الإجازة السنوية، ص 1].
  * Each chunk knows where it sits: its breadcrumb path
        دليل سياسات الموارد البشرية > الفصل الأول: الإجازات > الإجازة السنوية

How it works:
  Walk the blocks in order and keep a stack of open headings. A heading closes the current
  section and opens a new one; the stack gives the breadcrumb. Text before the first
  heading becomes an intro section named after the document. A heading immediately
  followed by a deeper heading has no text of its own, so it only appears in the path.

Safety net for very long sections (> MAX_SECTION_CHARS):
  split at the section's own numbered clauses (1. / ٢- / أ) / أولاً:), falling back to
  paragraph breaks, grouping whole clauses into parts. Every part keeps the section
  title "(جزء 1/3)" and the breadcrumb, so it is still self-explanatory.
"""

from dataclasses import dataclass, field

from config import MAX_SECTION_CHARS
from src.ingest.blocks import Block
from src.ingest.cleanup import CLAUSE_START


@dataclass
class Section:
    title: str
    path: list[str]
    blocks: list[Block] = field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None

    def add(self, block: Block) -> None:
        self.blocks.append(block)
        if block.page is not None:
            self.page_start = self.page_start or block.page
            self.page_end = block.page


def build_sections(blocks: list[Block], doc_title: str) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []          # open headings: (level, title)
    current: Section | None = None

    def close():
        if current and current.blocks:
            sections.append(current)

    for block in blocks:
        if block.type == "heading":
            close()
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            current = Section(title=block.text, path=[t for _, t in stack], page_start=block.page)
            continue
        if current is None:   # content before any heading
            current = Section(title=doc_title, path=[doc_title])
        current.add(block)
    close()
    return sections


def sections_to_chunks(sections: list[Section], source: str, meta: dict) -> list[dict]:
    chunks = []
    for section in sections:
        parts = _split_if_too_long(section)
        for i, part_blocks in enumerate(parts, start=1):
            title = section.title if len(parts) == 1 else f"{section.title} (جزء {i}/{len(parts)})"
            pages = [b.page for b in part_blocks if b.page is not None]
            chunks.append({
                "id": f"{source}#s{len(chunks)}",
                "source": source,
                "doc_title": meta.get("title", source),
                "version": meta.get("version", ""),
                "date": meta.get("date", ""),
                "url": meta.get("url", ""),
                "kind": meta.get("kind", ""),
                "category": meta.get("category", ""),
                "section_title": title,
                "section_path": " > ".join(section.path),
                "page_start": min(pages) if pages else section.page_start,
                "page_end": max(pages) if pages else section.page_end,
                "part": i,
                "parts": len(parts),
                "text": "\n".join(b.text for b in part_blocks),
            })
    return chunks


def embedding_text(chunk: dict) -> str:
    """What we embed: document title + version + where the section sits + its text."""
    version = f" - إصدار {chunk['version']}" if chunk["version"] else ""
    return f"{chunk['doc_title']}{version}\n{chunk['section_path']}\n{chunk['text']}"


def citation_label(chunk: dict) -> str:
    """How a chunk is cited: [document title، section، ص N]. Text files get pages from [[page N]] markers."""
    page = ""
    if chunk.get("page_start"):
        page = f"، ص {chunk['page_start']}" if chunk["page_start"] == chunk["page_end"] \
            else f"، ص {chunk['page_start']}-{chunk['page_end']}"
    section = "" if chunk["section_title"] == chunk["doc_title"] else f"، {chunk['section_title']}"
    return f"{chunk['doc_title']}{section}{page}"


# --- oversized sections ---------------------------------------------------------------

def _split_if_too_long(section: Section) -> list[list[Block]]:
    if sum(len(b.text) for b in section.blocks) <= MAX_SECTION_CHARS:
        return [section.blocks]

    # Units = whole clauses. A text block that contains several numbered clauses
    # (one per line, e.g. from TXT/OCR) is split at the clause starts.
    units: list[Block] = []
    for b in section.blocks:
        if b.type == "text" and "\n" in b.text:
            for clause in _split_clauses(b.text):
                units.append(Block("text", clause, page=b.page))
        else:
            units.append(b)

    # Group consecutive units into parts, starting a new part at a clause start when full.
    parts, current, size = [], [], 0
    for unit in units:
        starts_clause = bool(CLAUSE_START.match(unit.text)) or unit.type == "table"
        if current and size + len(unit.text) > MAX_SECTION_CHARS and (starts_clause or size > MAX_SECTION_CHARS // 2):
            parts.append(current)
            current, size = [], 0
        current.append(unit)
        size += len(unit.text)
    if current:
        parts.append(current)
    return parts


def _split_clauses(text: str) -> list[str]:
    clauses, current = [], []
    for line in text.split("\n"):
        if CLAUSE_START.match(line) and current:
            clauses.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        clauses.append("\n".join(current))
    return clauses
