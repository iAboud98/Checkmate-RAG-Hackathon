"""Pick the right loader for each file type. Every loader returns the same list of Blocks."""

import json
from pathlib import Path

from config import SUPPORTED_EXTENSIONS
from src.ingest.blocks import Block
from src.ingest.docx_loader import load_docx
from src.ingest.pdf_loader import load_pdf
from src.ingest.text_loader import load_markdown, load_text


def load_blocks(path: Path, meta: dict | None = None) -> list[Block]:
    meta = meta or {}
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path, force_ocr=bool(meta.get("ocr")))
    if suffix == ".docx":
        return load_docx(path)
    if suffix == ".md":
        return load_markdown(path)
    if suffix == ".txt":
        return load_text(path)
    raise ValueError(f"Unsupported file type: {path.name}")


def list_documents(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)


def load_metadata(folder: Path) -> dict:
    """metadata.json: {"file.pdf": {"title": ..., "version": "2025", "date": "2025-01-01", "ocr": false}}"""
    path = folder / "metadata.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_metadata(folder: Path, metadata: dict) -> None:
    (folder / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
