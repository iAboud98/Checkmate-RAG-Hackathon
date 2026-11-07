"""
The common format every loader produces: an ordered list of Blocks.

PDF, DOCX, Markdown and TXT look very different, but after loading they all become
    heading (with a level) / text (a paragraph) / table (rows as "header: value")
so the section builder (sections.py) only has to understand ONE format.
"""

from dataclasses import dataclass


@dataclass
class Block:
    type: str               # "heading" | "text" | "table"
    text: str
    level: int = 0          # headings only: 1 = top level (chapter), bigger = deeper
    page: int | None = None  # PDF page number; None for DOCX/MD/TXT (they have no pages)


def table_rows_to_text(rows: list[list[str]]) -> str:
    """First row = headers. Each other row becomes 'header: value | header: value' so values keep their meaning."""
    rows = [[c.strip() for c in r] for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        return "\n".join(" | ".join(r) for r in rows)
    header, body = rows[0], rows[1:]
    return "\n".join(" | ".join(f"{h}: {v}" for h, v in zip(header, row) if v) for row in body)
