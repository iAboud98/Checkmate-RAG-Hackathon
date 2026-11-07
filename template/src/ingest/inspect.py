"""Preview how a document will be chunked, with warnings. Used by the admin page and scripts/check_extraction.py."""

from pathlib import Path

from config import MAX_SECTION_CHARS
from src.ingest.cleanup import lam_alef_suspicion
from src.ingest.loaders import load_blocks
from src.ingest.sections import build_sections, sections_to_chunks

LAM_ALEF_WARNING_AT = 3


def inspect_document(path: Path, meta: dict) -> dict:
    blocks = load_blocks(path, meta)
    sections = build_sections(blocks, meta.get("title", path.stem))
    chunks = sections_to_chunks(sections, path.name, meta)
    text = "\n".join(b.text for b in blocks)
    warnings = []
    if not blocks:
        warnings.append('Nothing extracted. Scanned file? Set "ocr": true for it.')
    elif not any(b.type == "heading" for b in blocks):
        warnings.append("No headings found: the whole document is one section.")
    if (hits := lam_alef_suspicion(text)) >= LAM_ALEF_WARNING_AT:
        warnings.append(f'Lam-alef corruption suspected ({hits} hits, e.g. "عالمة" for "علامة"). '
                        'Set "ocr": true for this file, or OCR_ENGINE=vision.')
    if too_long := [c for c in chunks if len(c["text"]) > MAX_SECTION_CHARS]:
        warnings.append(f"{len(too_long)} chunk(s) above MAX_SECTION_CHARS={MAX_SECTION_CHARS}.")
    return {"blocks": len(blocks), "sections": len(sections), "chunks": chunks, "chars": len(text), "warnings": warnings}
