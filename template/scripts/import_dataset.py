"""
Import the organizers' dataset zip into data/raw/ (+ metadata.json).   Run once:

    python scripts/import_dataset.py ~/Downloads/documents_dataset.zip

What is in the zip and how we use it (see docs/LESSONS_LEARNED.md, A11):
  * json/documents.jsonl   249 Birzeit regulations scraped from Ritaj: clean UTF-8 text,
                           title, category and the official Ritaj URL.
  * pdfs/<regulation>.pdf  the same regulations rendered by ReportLab, but every Arabic word
                           is stored REVERSED, so their text layer is unusable.
    -> we index the clean text, and recover the PAGE of each paragraph by matching its words
       against the PDF's words (each PDF word read forwards and backwards). Citations keep "ص N".
  * The real PDFs (student guide, the 4 study plans, one scanned ministry decision) are copied
    as they are; the PDF loader (+ OCR for the scanned one) handles them.

Only student-facing regulations are imported (domain.STUDENT_CATEGORIES / STUDENT_TITLE_KEYWORDS).
Staff, HR, finance and museum documents are skipped on purpose: questions about them get refused.
"""

import json
import re
import sys
import zipfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import domain  # noqa: E402
from config import DOCS_DIR  # noqa: E402
from src.ingest.normalize import normalize_arabic  # noqa: E402

# Real PDFs copied as they are: zip path -> metadata.
REAL_PDFS = {
    "pdfs/BirzeitUniversity_main_document.pdf": {
        "file": "دليل جامعة بيرزيت لدرجة البكالوريوس 2024-2025.pdf",
        "title": "دليل جامعة بيرزيت لدرجة البكالوريوس 2024-2025", "version": "2024-2025",
        "category": "دليل الطالب", "kind": "guide"},
    "pdfs/1_Computer Engineering_4_YEAR_PLAN_APRIL_25_2026.pdf": {
        "file": "خطة هندسة الحاسوب 2026.pdf",
        "title": "الخطة الدراسية لبكالوريوس هندسة الحاسوب (نيسان 2026)", "version": "2026", "date": "2026-04-25",
        "category": "الخطط الدراسية", "kind": "plan"},
    "pdfs/2_Network_ENG_Security_4_YEAR_PLAN_APRIL_25_2026.pdf": {
        "file": "خطة هندسة الشبكات وأمن المعلومات 2026.pdf",
        "title": "الخطة الدراسية لبكالوريوس هندسة الشبكات وأمن المعلومات (نيسان 2026)", "version": "2026",
        "date": "2026-04-25", "category": "الخطط الدراسية", "kind": "plan"},
    "pdfs/4_Smart Energy Systems Engineering_4_YEAR_PLAN_APEIL_25_2026.pdf": {
        "file": "خطة هندسة أنظمة الطاقة الذكية 2026.pdf",
        "title": "الخطة الدراسية لبكالوريوس هندسة أنظمة الطاقة الذكية (نيسان 2026)", "version": "2026",
        "date": "2026-04-25", "category": "الخطط الدراسية", "kind": "plan"},
    "pdfs/10463.pdf": {
        "file": "قرار وزاري بشأن متطلبات الدرجة العلمية 2021.pdf",
        "title": "قرار وزاري بشأن تعليمات متطلبات الدرجة العلمية للتعليم بالانتظام (2021)", "version": "2021",
        "category": "قرارات وزارة التعليم العالي", "kind": "decision", "ocr": True},
}
# The EE plan's file name contains a broken character, so it is matched by prefix.
REAL_PDF_PREFIXES = {
    "pdfs/3_Electrical Engineering": {
        "file": "خطة الهندسة الكهربائية 2026.pdf",
        "title": "الخطة الدراسية لبكالوريوس الهندسة الكهربائية (نيسان 2026)", "version": "2026",
        "date": "2026-04-25", "category": "الخطط الدراسية", "kind": "plan"},
}

YEAR = re.compile(r"(19|20)\d{2}")
WORD = re.compile(r"\w+")


def zip_name(info: zipfile.ZipInfo) -> str:
    """Zip files made on some systems store UTF-8 names flagged as cp437."""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("utf-8")
    except UnicodeError:
        return info.filename


def is_student_facing(doc: dict) -> bool:
    if any(w in doc["title"] for w in domain.STAFF_TITLE_WORDS):
        return False
    if any(w in doc["title"] for w in domain.GRADUATE_TITLE_WORDS) and "البكالوريوس" not in doc["title"]:
        return False
    if any(c in domain.STUDENT_CATEGORIES for c in doc["category"]):
        return True
    return any(k in doc["title"] for k in domain.STUDENT_TITLE_KEYWORDS)


def version_of(title: str) -> str:
    m = YEAR.search(title)
    if not m:
        return ""
    return f"ما قبل {m.group(0)}" if "قبل" in title else m.group(0)


def _norm_words(text: str) -> list[str]:
    return [w for w in WORD.findall(normalize_arabic(text)) if len(w) > 2]


def pdf_page_words(pdf_bytes: bytes) -> list[set[str]]:
    """One set of normalized words per page; each PDF word added forwards AND reversed."""
    pages = []
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            words = set()
            for w in page.get_text("words"):
                for variant in (w[4], w[4][::-1]):
                    words.update(_norm_words(variant))
            pages.append(words)
    return pages


def align_pages(paragraphs: list[str], pages: list[set[str]]) -> list[int]:
    """Give each paragraph a page (1-based) so that pages never go backwards and the total word
    overlap is as large as possible (dynamic programming, like aligning two sequences).
    A greedy "best page per paragraph" choice fails: one noisy paragraph can jump far ahead."""
    n_pages = len(pages)
    scores = [[sum(w in pages[p] for w in _norm_words(para)) for p in range(n_pages)] for para in paragraphs]
    best = [scores[0][:]] if paragraphs else []
    back = []
    for i in range(1, len(paragraphs)):
        row, ptr, run_max, run_arg = [], [], float("-inf"), 0
        for p in range(n_pages):
            if best[i - 1][p] > run_max:   # best previous page q <= p
                run_max, run_arg = best[i - 1][p], p
            row.append(scores[i][p] + run_max)
            ptr.append(run_arg)
        best.append(row)
        back.append(ptr)
    if not best:
        return []
    p = max(range(n_pages), key=lambda q: best[-1][q])
    result = [p]
    for ptr in reversed(back):
        p = ptr[p]
        result.append(p)
    return [q + 1 for q in reversed(result)]


def add_page_markers(text: str, pages: list[set[str]]) -> str:
    """Put a [[page N]] line before each paragraph that starts a new PDF page."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not pages or not paragraphs:
        return text
    out, current = [], None
    for para, page in zip(paragraphs, align_pages(paragraphs, pages)):
        if page != current:
            current = page
            out.append(f"[[page {page}]]")
        out.append(para)
    return "\n\n".join(out)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python scripts/import_dataset.py path/to/documents_dataset.zip")
    archive = zipfile.ZipFile(Path(sys.argv[1]).expanduser())
    files = {zip_name(i): i for i in archive.infolist() if not i.is_dir()}
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {}

    # 1. Regulations: clean text + page markers recovered from the reversed PDFs.
    docs = [json.loads(line) for line in archive.read(files["json/documents.jsonl"]).decode("utf-8").splitlines()]
    kept = [d for d in docs if is_student_facing(d) and d["files"].get("text") in files]
    for d in kept:
        text = archive.read(files[d["files"]["text"]]).decode("utf-8")
        pdf = d["files"].get("pdf")
        if pdf in files:
            text = add_page_markers(text, pdf_page_words(archive.read(files[pdf])))
        name = Path(d["files"]["text"]).name.replace("／", "-")
        (DOCS_DIR / name).write_text(text, encoding="utf-8")
        metadata[name] = {"title": d["title"], "version": version_of(d["title"]), "date": "",
                          "category": d["category"][0] if d["category"] else "", "url": d["url"],
                          "kind": "regulation", "ocr": False}
        print(f"  regulation  {name}")

    # 2. Real PDFs: copied as they are.
    real = dict(REAL_PDFS)
    for prefix, meta in REAL_PDF_PREFIXES.items():
        real.update({n: meta for n in files if n.startswith(prefix)})
    for zpath, meta in real.items():
        if zpath not in files:
            print(f"  !! missing in zip: {zpath}")
            continue
        (DOCS_DIR / meta["file"]).write_bytes(archive.read(files[zpath]))
        metadata[meta["file"]] = {"title": meta["title"], "version": meta.get("version", ""),
                                  "date": meta.get("date", ""), "category": meta["category"], "url": "",
                                  "kind": meta["kind"], "ocr": meta.get("ocr", False)}
        print(f"  pdf         {meta['file']}")

    (DOCS_DIR / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nImported {len(kept)} of {len(docs)} regulations + {len(real)} PDFs into {DOCS_DIR}")


if __name__ == "__main__":
    main()
