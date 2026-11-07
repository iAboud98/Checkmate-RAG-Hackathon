"""
MILESTONE 1: Load PDFs into clean text, one record per page.

Output: a list of dicts like
    {"text": "...", "source": "registration_and_fees.pdf", "page": 2}

We keep the page number on purpose: it's what lets the final answer cite
"[registration_and_fees.pdf, ص 2]".

Three Arabic-PDF problems this file handles:
  1. Word order. PDFs store text in *visual* order. For Arabic mixed with
     numbers this often comes out scrambled ("%15 لا يجوز..."). We rebuild each
     line from its words, sorted right-to-left by their x position.
  2. Tables. Plain extraction mashes cells together and loses the headers.
     We detect tables and write each row as "header: value | header: value",
     so every chunk containing a row still knows what each number means.
  3. Scanned pages (images, no text layer). We fall back to OCR (Tesseract).
"""

import re
from itertools import groupby
from pathlib import Path

import pymupdf

from config import OCR_LANG

MIN_TEXT_CHARS = 20  # fewer characters than this on a page = probably a scanned image
BIDI_MARKS = re.compile("[‎‏‪-‮]")


def load_pdf(path: Path) -> list[dict]:
    pages = []
    with pymupdf.open(path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = extract_page_text(page)
            if len(text.strip()) < MIN_TEXT_CHARS:
                text = ocr_page(page)
            if text.strip():
                pages.append({"text": text, "source": path.name, "page": page_number})
    return pages


def load_folder(folder: Path) -> list[dict]:
    pages = []
    for path in sorted(folder.glob("*.pdf")):
        pages.extend(load_pdf(path))
    return pages


# --- helpers ---------------------------------------------------------------

def extract_page_text(page: pymupdf.Page) -> str:
    tables = page.find_tables().tables
    table_boxes = [pymupdf.Rect(t.bbox) for t in tables]

    # Every word on the page: (x0, y0, x1, y1, word, block_no, line_no, word_no)
    words = page.get_text("words")
    # Words inside a table are handled by table_to_text instead.
    words = [w for w in words if not any(box.contains(_center(w)) for box in table_boxes)]

    # Each table becomes one text block, positioned where the table starts.
    pieces = [(t.bbox[1], table_to_text(t, page)) for t in tables]

    # Group the remaining words by (block, line), then sort each line right-to-left.
    words.sort(key=lambda w: (w[5], w[6], -w[0]))
    for _, line_words in groupby(words, key=lambda w: (w[5], w[6])):
        line_words = list(line_words)
        pieces.append((line_words[0][1], " ".join(w[4] for w in line_words)))

    # Put tables and lines back in top-to-bottom reading order.
    pieces.sort(key=lambda p: p[0])
    return "\n".join(_tidy(text) for _, text in pieces)


def _tidy(line: str) -> str:
    """Small fixes for leftovers of visual ordering."""
    line = re.sub(r"\s+([.,:،؛])", r"\1", line)   # "النهائي ." -> "النهائي."
    line = re.sub(r"%(\d+)", r"\1%", line)        # "%15" -> "15%"
    return line


def table_to_text(table, page: pymupdf.Page) -> str:
    """Turn a table into lines like 'رقم المساق: CPE201 | اسم المساق: هياكل البيانات | ...'."""
    words = page.get_text("words")
    rows = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            if cell is None:
                cells.append("")
                continue
            box = pymupdf.Rect(cell)
            inside = [w for w in words if box.contains(_center(w))]
            inside.sort(key=lambda w: (round(w[1]), -w[0]))  # top-to-bottom, then right-to-left
            cells.append(" ".join(w[4] for w in inside))
        # PDF tables in RTL documents list cells left-to-right; reverse to reading order.
        rows.append(list(reversed(cells)))

    header, body = rows[0], rows[1:]
    lines = []
    for row in body:
        lines.append(" | ".join(f"{h}: {v}" for h, v in zip(header, row) if v))
    return "\n".join(lines)


def ocr_page(page: pymupdf.Page) -> str:
    """
    Scanned page -> image -> Tesseract OCR. Arabic needs: brew install tesseract-lang.

    OCR_LANG trade-off (tested on our sample pages):
      "ara+eng"  keeps Latin course codes (CPE201) but sometimes misreads an Arabic word as Latin (كلية -> AUS)
      "ara"      reads Arabic words better but drops Latin codes entirely
    OCR also reads tables column by column, so row structure is lost.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    pix = page.get_pixmap(dpi=300)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    try:
        text = pytesseract.image_to_string(image, lang=OCR_LANG)
    except pytesseract.TesseractError:
        # Arabic language data not installed: fall back to English only.
        text = pytesseract.image_to_string(image, lang="eng")
    return BIDI_MARKS.sub("", text)  # Tesseract inserts invisible direction marks around Latin text


def _center(word) -> pymupdf.Point:
    return pymupdf.Point((word[0] + word[2]) / 2, (word[1] + word[3]) / 2)
