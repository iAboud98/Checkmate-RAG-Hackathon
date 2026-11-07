"""
PDF -> Blocks (headings / paragraphs / tables), ready for section-based chunking.

How headings are found, in order of trust:
  1. The PDF's own outline/bookmarks (doc.get_toc()), if the file has one.
  2. Font size: the most common size is body text, and clearly bigger lines are headings.
     Each distinct bigger size is a level (biggest = level 1). Bold short lines count too.
  3. Arabic structure words on short lines: الباب / الفصل / المادة 5 / أولاً ...

Arabic PDF fixes carried over from the demo (docs/LESSONS_LEARNED.md):
  A2 rebuild each line from its words sorted right-to-left (fixes misplaced numbers)
  A3 tables: find_tables() for cell boxes, words inside each cell, rows as "header: value"
  A6 drop headers/footers repeated across pages
  C1b scanned pages (no text layer) go to OCR
"""

from collections import Counter
from pathlib import Path

import pymupdf

from config import MIN_TEXT_CHARS
from src.ingest.blocks import Block, table_rows_to_text
from src.ingest.cleanup import (CLAUSE_START, find_repeated_lines, is_repeated, regex_heading_rank, tidy)
from src.ingest.ocr import ocr_page_blocks

HEADING_SIZE_RATIO = 1.15   # a line at least 15% bigger than body text is a heading
PARAGRAPH_GAP_RATIO = 0.6   # vertical gap (as a fraction of font size) that separates paragraphs
BOLD_HEADING_MAX_CHARS = 80


def load_pdf(path: Path, force_ocr: bool = False) -> list[Block]:
    with pymupdf.open(path) as pdf:
        pages = [_read_page(page, i, force_ocr) for i, page in enumerate(pdf, start=1)]
        toc = {(p, _key(title)): lvl for lvl, title, p in pdf.get_toc()}

    # Headers/footers: lines repeated at the top/bottom of many pages.
    repeated = find_repeated_lines([[l["text"] for l in p["lines"]] for p in pages])

    lines = [l for p in pages for l in p["lines"] if not is_repeated(l["text"], repeated)]
    body_size = _body_font_size(lines)
    size_levels = _heading_size_levels(lines, body_size)

    blocks: list[Block] = []
    for p in pages:
        if p["ocr_blocks"] is not None:          # scanned page: OCR already produced blocks
            blocks.extend(p["ocr_blocks"])
            continue
        items = [l for l in p["lines"] if not is_repeated(l["text"], repeated)] + p["tables"]
        items.sort(key=lambda it: it["y"])
        paragraph, prev = [], None

        def flush():
            if paragraph:
                blocks.append(Block("text", " ".join(paragraph), page=p["page"]))
                paragraph.clear()

        for it in items:
            if it.get("table"):
                flush()
                blocks.append(Block("table", it["text"], page=p["page"]))
                continue
            level = _heading_level(it, body_size, size_levels, toc, p["page"])
            if level:
                flush()
                blocks.append(Block("heading", it["text"], level=level, page=p["page"]))
                prev = None
                continue
            else:
                # Wrapped lines of one paragraph sit close together; a bigger vertical gap
                # or a numbered clause ("1. ...") starts a new paragraph.
                gap = it["y"] - prev["y1"] if prev and not prev.get("table") else 1e9
                if gap > PARAGRAPH_GAP_RATIO * it["size"] or CLAUSE_START.match(it["text"]):
                    flush()
                paragraph.append(it["text"])
            prev = it
        flush()
    return blocks


# --- page reading -------------------------------------------------------------

def _read_page(page: pymupdf.Page, page_no: int, force_ocr: bool) -> dict:
    raw_text = page.get_text().strip()
    if force_ocr or len(raw_text) < MIN_TEXT_CHARS:
        return {"page": page_no, "lines": [], "tables": [], "ocr_blocks": ocr_page_blocks(page, page_no)}

    # use_layout=False: PyMuPDF's optional ONNX layout model segfaulted on the EE study plan (LESSONS A12).
    # Line-based detection is enough for ruled tables like the study plans.
    tables = page.find_tables(use_layout=False).tables
    table_boxes = [pymupdf.Rect(t.bbox) for t in tables]
    words = page.get_text("words")    # (x0, y0, x1, y1, word, block, line, word_no)

    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            box = pymupdf.Rect(line["bbox"])
            if any(tb.contains(box.tl + (box.br - box.tl) * 0.5) for tb in table_boxes):
                continue
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            # Lesson A2: rebuild the line from its words, right-to-left.
            inside = [w for w in words if box.contains(_center(w))]
            inside.sort(key=lambda w: -w[0])
            text = tidy(" ".join(w[4] for w in inside))
            if not text:
                continue
            chars = sum(len(s["text"]) for s in spans)
            lines.append({
                "text": text,
                "y": box.y0,
                "y1": box.y1,
                "size": round(sum(s["size"] * len(s["text"]) for s in spans) / chars, 1),
                "bold": all(s["flags"] & 16 or "bold" in s["font"].lower() for s in spans),
            })

    table_items = [{"table": True, "y": t.bbox[1], "text": _table_text(t, words)} for t in tables]
    return {"page": page_no, "lines": lines, "tables": table_items, "ocr_blocks": None}


def _table_text(table, words) -> str:
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            if cell is None:
                cells.append("")
                continue
            box = pymupdf.Rect(cell)
            inside = sorted((w for w in words if box.contains(_center(w))), key=lambda w: (round(w[1]), -w[0]))
            cells.append(tidy(" ".join(w[4] for w in inside)))
        rows.append(list(reversed(cells)))   # PDF cells come left-to-right; Arabic reads right-to-left
    return table_rows_to_text(rows)


# --- heading detection -----------------------------------------------------------

def _body_font_size(lines: list[dict]) -> float:
    sizes = Counter()
    for l in lines:
        sizes[l["size"]] += len(l["text"])
    return sizes.most_common(1)[0][0] if sizes else 0.0


def _heading_size_levels(lines: list[dict], body: float) -> dict[float, int]:
    big = sorted({l["size"] for l in lines if l["size"] >= body * HEADING_SIZE_RATIO and len(l["text"]) <= 120},
                 reverse=True)
    return {size: level for level, size in enumerate(big, start=1)}


def _heading_level(line: dict, body: float, size_levels: dict, toc: dict, page: int) -> int | None:
    text = line["text"]
    if toc:   # 1. trust the PDF's own outline when it has one
        level = toc.get((page, _key(text)))
        if level:
            return level
    if line["size"] in size_levels:   # 2. font size
        return size_levels[line["size"]]
    deepest = len(size_levels)
    if line["bold"] and len(text) <= BOLD_HEADING_MAX_CHARS and not text.endswith((".", "،")):
        return deepest + 1
    rank = regex_heading_rank(text)   # 3. Arabic structure words
    if rank:
        return deepest + 1 + rank
    return None


def _key(text: str) -> str:
    return "".join(text.split())


def _center(w) -> pymupdf.Point:
    return pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
