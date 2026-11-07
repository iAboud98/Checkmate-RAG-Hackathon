"""
Scanned pages (no text layer) -> Blocks.

OCR_ENGINE=tesseract (default, offline, ~2 s/page). Headings are found only by Arabic
    structure words (الفصل / المادة ...) because OCR has no font information.
    Known issues (lesson C1b): misreads some words, and reads TABLES column by column.
OCR_ENGINE=vision: the page image goes to an OpenAI vision model, which returns Markdown
    with real headings and tables. Slower and costs tokens, but keeps structure.
"""

import base64

import pymupdf

from config import OCR_ENGINE, OCR_LANG, VISION_MODEL
from src.ingest.blocks import Block
from src.ingest.cleanup import BIDI_MARKS, regex_heading_rank

VISION_PROMPT = """انسخ النص الموجود في صورة هذه الصفحة كما هو، بصيغة Markdown:
- العناوين بعلامات # حسب مستواها.
- الجداول بصيغة جدول Markdown مع صف العناوين.
- لا تلخص ولا تضف أي شيء غير موجود في الصورة. اكتب النص فقط."""


def ocr_page_blocks(page: pymupdf.Page, page_no: int) -> list[Block]:
    if OCR_ENGINE == "vision":
        from src.ingest.text_loader import markdown_to_blocks
        return markdown_to_blocks(_vision_markdown(page), page=page_no)
    return _tesseract_blocks(page, page_no)


def _tesseract_blocks(page: pymupdf.Page, page_no: int) -> list[Block]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return []
    pix = page.get_pixmap(dpi=300)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    try:
        text = pytesseract.image_to_string(image, lang=OCR_LANG)
    except pytesseract.TesseractError:   # Arabic data missing: brew install tesseract-lang
        text = pytesseract.image_to_string(image, lang="eng")
    text = BIDI_MARKS.sub("", text)

    blocks, paragraph = [], []
    for line in text.splitlines() + [""]:
        line = line.strip()
        rank = regex_heading_rank(line)
        if not line or rank:
            if paragraph:
                blocks.append(Block("text", " ".join(paragraph), page=page_no))
                paragraph = []
            if rank:
                blocks.append(Block("heading", line, level=10 + rank, page=page_no))
        else:
            paragraph.append(line)
    return blocks


def _vision_markdown(page: pymupdf.Page) -> str:
    from src.openai_client import get_client
    png = page.get_pixmap(dpi=200).tobytes("png")
    image_url = "data:image/png;base64," + base64.b64encode(png).decode()
    response = get_client().chat.completions.create(
        model=VISION_MODEL,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": VISION_PROMPT},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]}],
    )
    return response.choices[0].message.content or ""
