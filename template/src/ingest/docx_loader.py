"""
Word (.docx) -> Blocks. The most reliable format for sections: Word stores headings as
styles ("Heading 1", "Heading 2", ... or "Title"), so no guessing is needed.

Fallbacks, for documents where the author just made text bold or big instead of using styles:
  * a short paragraph whose runs are all bold = heading
  * Arabic structure words (الفصل / المادة 3 / أولاً ...) on a short paragraph = heading
Tables become "header: value" rows. DOCX has no fixed pages, so blocks have page=None.
"""

import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from src.ingest.blocks import Block, table_rows_to_text
from src.ingest.cleanup import BIDI_MARKS, regex_heading_rank

HEADING_STYLE = re.compile(r"(heading|عنوان)\s*(\d)", re.IGNORECASE)
BOLD_HEADING_MAX_CHARS = 80


def load_docx(path: Path) -> list[Block]:
    doc = Document(str(path))
    blocks = []
    # Walk the body in order so paragraphs and tables stay interleaved correctly.
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            block = _paragraph_block(Paragraph(child, doc))
            if block:
                blocks.append(block)
        elif tag == "tbl":
            rows = [[cell.text for cell in row.cells] for row in Table(child, doc).rows]
            text = table_rows_to_text(rows)
            if text:
                blocks.append(Block("table", text))
    return blocks


def _paragraph_block(p: Paragraph) -> Block | None:
    text = BIDI_MARKS.sub("", p.text).strip()
    if not text:
        return None
    level = _style_level(p)
    if level is None and len(text) <= BOLD_HEADING_MAX_CHARS:
        runs = [r for r in p.runs if r.text.strip()]
        if runs and all(r.bold for r in runs) and not text.endswith((".", "،")):
            level = 7
        elif (rank := regex_heading_rank(text)):
            level = 7 + rank
    return Block("heading", text, level=level) if level is not None else Block("text", text)


def _style_level(p: Paragraph) -> int | None:
    style = p.style
    names = f"{style.name} {style.style_id}" if style is not None else ""
    if "title" in names.lower() or "عنوان رئيسي" in names:
        return 0
    match = HEADING_STYLE.search(names)
    if match:
        return int(match.group(2))
    # Some documents set an outline level directly on the paragraph instead of a style.
    outline = p._p.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}outlineLvl")
    if outline is not None:
        return int(outline.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")) + 1
    return None
