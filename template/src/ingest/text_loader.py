"""
Markdown and plain text -> Blocks.

Markdown: "#" = level 1, "##" = level 2 ... ; tables "| a | b |" become "header: value" rows.
Plain text: paragraphs are separated by blank lines; a short line that matches an Arabic
structure word (الفصل / المادة 3 / أولاً ...) is a heading.
"""

import re
from pathlib import Path

from src.ingest.blocks import Block, table_rows_to_text
from src.ingest.cleanup import BIDI_MARKS, regex_heading_rank

MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
MD_TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{2,}")
# "[[page N]]" lines are written by scripts/import_dataset.py: the page this text has in the
# official PDF, recovered by word matching. They set Block.page so citations can show "ص N".
PAGE_MARKER = re.compile(r"^\[\[page (\d+)\]\]$")


def load_markdown(path: Path) -> list[Block]:
    return markdown_to_blocks(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> list[Block]:
    text = BIDI_MARKS.sub("", path.read_text(encoding="utf-8"))
    blocks, paragraph = [], []
    page = None

    def flush():
        if paragraph:
            blocks.append(Block("text", " ".join(paragraph), page=page))
            paragraph.clear()

    for line in text.splitlines():
        line = line.strip()
        marker = PAGE_MARKER.match(line)
        if marker:
            flush()
            page = int(marker.group(1))
            continue
        rank = regex_heading_rank(line)
        if rank:
            flush()
            blocks.append(Block("heading", line, level=rank, page=page))
        elif not line:
            flush()
        else:
            paragraph.append(line)
    flush()
    return blocks


def markdown_to_blocks(markdown: str, page: int | None = None) -> list[Block]:
    blocks, paragraph, table = [], [], []

    def flush():
        if paragraph:
            blocks.append(Block("text", " ".join(paragraph), page=page))
            paragraph.clear()
        if table:
            blocks.append(Block("table", table_rows_to_text(table), page=page))
            table.clear()

    for line in BIDI_MARKS.sub("", markdown).splitlines():
        line = line.strip()
        heading = MD_HEADING.match(line)
        if heading:
            flush()
            blocks.append(Block("heading", heading.group(2).strip(" #*"), level=len(heading.group(1)), page=page))
        elif line.startswith("|"):
            if paragraph:
                blocks.append(Block("text", " ".join(paragraph), page=page))
                paragraph.clear()
            if not MD_TABLE_SEPARATOR.match(line):
                table.append([c.strip() for c in line.strip("|").split("|")])
        elif not line:
            flush()
        else:
            if table:
                flush()
            paragraph.append(line.lstrip("-*• ").strip() if line[:2] in ("- ", "* ", "• ") else line)
    flush()
    return blocks
