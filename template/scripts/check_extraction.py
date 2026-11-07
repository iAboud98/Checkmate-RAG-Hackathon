"""
RUN THIS FIRST on the organizers' documents, before building the index (lessons A1, F2).

For every document it prints the section tree that chunking will produce (titles, pages,
sizes, which sections were split) and warnings: nothing extracted, no headings found,
lam-alef corruption ("علامة" extracting as "عالمة" = broken PDF text layer; fix with
"ocr": true for that file in metadata.json, or OCR_ENGINE=vision).

Usage:
    python scripts/check_extraction.py                  # all docs in DOCS_DIR (default data/raw)
    python scripts/check_extraction.py path/to/folder   # another folder
    python scripts/check_extraction.py file.pdf --text  # also print each chunk's text
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DOCS_DIR  # noqa: E402
from src.ingest.inspect import inspect_document  # noqa: E402
from src.ingest.loaders import list_documents, load_metadata  # noqa: E402
from src.ingest.sections import citation_label  # noqa: E402


def check(path: Path, meta: dict, show_text: bool) -> None:
    report = inspect_document(path, meta)
    print(f"\n{'=' * 80}\n{path.name}   title: {meta.get('title', path.stem)}   version: {meta.get('version', '-')}")
    print(f"{report['blocks']} blocks -> {report['sections']} sections -> {len(report['chunks'])} chunks   ({report['chars']} chars)")
    for w in report["warnings"]:
        print(f"  !! {w}")
    for c in report["chunks"]:
        depth = c["section_path"].count(" > ")
        split = "  [split]" if c["parts"] > 1 else ""
        print(f"  {'  ' * depth}• {c['section_title']}   [{citation_label(c)}]   {len(c['text'])} chars{split}")
        if show_text:
            for line in c["text"].splitlines():
                print(f"  {'  ' * depth}    | {line}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_text = "--text" in sys.argv
    target = Path(args[0]) if args else DOCS_DIR
    if target.is_file():
        check(target, load_metadata(target.parent).get(target.name, {}), show_text)
        return
    metadata = load_metadata(target)
    docs = list_documents(target)
    if not docs:
        print(f"No documents in {target}")
    for path in docs:
        check(path, metadata.get(path.name, {}), show_text)


if __name__ == "__main__":
    main()
