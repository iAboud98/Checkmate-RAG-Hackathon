"""
Turn the Computer Engineering 4-year plan PDF into structured data for the course tracker:

    python scripts/parse_study_plan.py        ->  data/plans/computer_engineering.json

Where each field comes from (all from "خطة هندسة الحاسوب 2026.pdf", nothing typed by hand):
  * year / semester / code / credits        : the study-plan table on pages 5-7
  * English name                            : the course-description headers (else the table)
  * prerequisites                           : the English "Prerequisite:" lines in the course
                                              descriptions (pages 7-34)
  * category                                : the requirement split on page 1 (university 16,
                                              free 3, electives 16, the rest = faculty + major)
Courses whose prerequisites could not be read get "needs_review": true. A teammate checks the
JSON against the PDF before the demo.
"""

import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DOCS_DIR, ROOT  # noqa: E402

PDF = DOCS_DIR / "خطة هندسة الحاسوب 2026.pdf"
OUT = ROOT / "data" / "plans" / "computer_engineering.json"
TABLE_PAGES = (5, 6, 7)   # page 7 holds the last two rows of semester 8
TERMS = ["Y1-S1", "Y1-S2", "Y1-Summer", "Y2-S1", "Y2-S2", "Y3-S1", "Y3-S2", "Y3-Summer", "Y4-S1", "Y4-S2"]
TERM_LABELS = {"Y1-S1": "السنة الأولى · الفصل الأول", "Y1-S2": "السنة الأولى · الفصل الثاني",
               "Y1-Summer": "السنة الأولى · الصيفي", "Y2-S1": "السنة الثانية · الفصل الأول",
               "Y2-S2": "السنة الثانية · الفصل الثاني", "Y3-S1": "السنة الثالثة · الفصل الأول",
               "Y3-S2": "السنة الثالثة · الفصل الثاني", "Y3-Summer": "السنة الثالثة · الصيفي",
               "Y4-S1": "السنة الرابعة · الفصل الأول", "Y4-S2": "السنة الرابعة · الفصل الثاني"}
# Requirement split, plan page 1.
REQUIREMENTS = {"university": 16, "free": 3, "major_elective": 16, "required": 103}
CATEGORY_LABELS = {"university": "متطلبات الجامعة", "free": "مساقات حرة",
                   "major_elective": "متطلبات التخصص الاختيارية", "required": "متطلبات الكلية والتخصص الإجبارية"}

CODE = re.compile(r"^(?:[A-Z]{4}\d{3,5}|COMP2\s*x\s*3\s*x|Arabic136|DepElectv[\d\s,\n]*|UniElective|LabElective)$")
REF = re.compile(r"\b[A-Z]{4}\d{3,5}\b")


def course_category(code: str) -> str:
    if code.startswith(("ARAB", "ENGC", "ENGL", "CULS")):
        return "university"
    if code == "UniElective":
        return "free"
    if code.startswith(("DepElectv", "LabElective")):
        return "major_elective"
    return "required"


def clean_code(raw: str) -> str:
    raw = re.sub(r"\s+", "", raw)
    if raw == "Arabic136":
        return "ARAB136"
    if raw.startswith("COMP2x3x"):
        return "COMP23xx"   # written like this in the plan: "COMP2321 or COMP242 or COMP2421 or COMP23xx"
    return raw.replace(",", "-")


def split_camel(name: str) -> str:
    name = re.sub(r"\s+", " ", name.replace("\n", " ")).strip(" .")
    return re.sub(r"(?<=[a-z&])(?=[A-Z])", " ", name)


def parse_table(doc: pymupdf.Document) -> list[dict]:
    courses, term, term_has_courses = [], 0, False
    for page_no in TABLE_PAGES:
        for table in doc[page_no - 1].find_tables().tables:
            for row in table.extract():
                cells = [c.strip() for c in row if c not in (None, "") and c.strip()]
                if not cells:
                    if term_has_courses:
                        term, term_has_courses = term + 1, False
                    continue
                if any(re.fullmatch(r"Sem\d|Summer", c) for c in cells) and term_has_courses:
                    term, term_has_courses = term + 1, False
                cells = [c for c in cells if not re.fullmatch(r"(First|Second|Third|Fourth) Year|Sem\d|Summer", c)]
                if cells[:3] == ["COMP2", "3", "x"]:   # "COMP23xx" is split over three cells
                    cells = ["COMP2 x 3 x"] + cells[3:]
                code_i = next((i for i, c in enumerate(cells) if CODE.match(c)), None)
                if code_i is None:
                    latin = [c for c in cells if re.search(r"[A-Za-z]{3}", c) and c not in ("Year", "CourseCode")]
                    if courses and latin and term_has_courses and "Course" not in " ".join(cells):
                        courses[-1]["name_en"] += " " + split_camel(latin[0])   # name wrapped to the next row
                    continue
                rest = cells[code_i + 1:]
                credits = next((int(c) for c in rest if re.fullmatch(r"[1-9]", c)), None)
                name = next((c for c in rest if re.search(r"[A-Za-z]{2}", c) and not c.isdigit()), "")
                code = clean_code(cells[code_i])
                courses.append({"code": code, "name_en": split_camel(name), "credits": credits,
                                "category": course_category(code), "term": TERMS[min(term, len(TERMS) - 1)],
                                "page": page_no})
                term_has_courses = True
    return courses


ARABIC = re.compile(r"[\u0600-\u06FF]")
TITLE = re.compile(r"^[A-Z][A-Za-z\-]+(\s+[A-Za-z0-9&\-.,()/]+)*$")


def parse_descriptions(doc: pymupdf.Document) -> tuple[dict[str, dict], dict[str, str]]:
    """Returns (prerequisites, English names).
    prerequisites: code -> {"groups": [[A, B], [C]], "text": "...", "page": N}  (groups = AND of ORs).
    Each description is "CODE English title / text / Prerequisite: ..." followed by an Arabic block
    that starts with the same code. A prerequisite line is only kept while we are inside an English
    description; when the header can't be read we leave it empty (needs_review) rather than guess."""
    found, names, current = {}, {}, None
    for page in doc:
        lines = page.get_text().splitlines()
        for i, line in enumerate(lines):
            s = line.strip()
            header = re.match(r"^([A-Z]{4}\d{3,5})\s*(.*)$", s)
            if header:
                nxt = header.group(2).strip() or (lines[i + 1].strip() if i + 1 < len(lines) else "")
                if ARABIC.search(nxt):
                    current = None                       # Arabic half of a description
                elif TITLE.match(nxt) and len(nxt) < 70:  # "ENCS3320 Computer Networks"
                    current = header.group(1)
                    names.setdefault(current, nxt.strip(" ."))
                continue
            m = re.search(r"Prerequisites?\s*:\s*(.*)$", s)
            if not m or not current or current in found:
                continue
            text = m.group(1)
            j = i + 1
            while j < len(lines) and (text.rstrip().endswith(("or", ",", "(", "and")) or not text.strip()):
                text += " " + lines[j].strip()
                j += 1
            groups = []
            for part in re.split(r",|\band\b", text):
                codes = REF.findall(part)
                if codes:
                    groups.append(codes)
            found[current] = {"groups": groups, "text": text.strip(), "page": page.number + 1}
    return found, names


def main() -> None:
    with pymupdf.open(PDF) as doc:
        courses = parse_table(doc)
        prereqs, names = parse_descriptions(doc)
    for c in courses:
        c["name_en"] = names.get(c["code"], c["name_en"])
        p = prereqs.get(c["code"])
        c["prereqs"] = p["groups"] if p else []
        c["prereq_text"] = p["text"] if p else ""
        c["prereq_page"] = p["page"] if p else None
        placeholder = c["category"] in ("free", "major_elective") or c["code"] == "COMP23xx"
        c["needs_review"] = c["credits"] is None or (not p and not placeholder and c["term"] not in ("Y1-S1",))
    plan = {
        "program": "هندسة الحاسوب", "program_en": "Computer Engineering", "source": PDF.name,
        "doc_title": "الخطة الدراسية لبكالوريوس هندسة الحاسوب (نيسان 2026)", "table_pages": list(TABLE_PAGES),
        "total_hours": 138, "requirements": REQUIREMENTS, "category_labels": CATEGORY_LABELS,
        "terms": TERMS, "term_labels": TERM_LABELS, "courses": courses,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(c["credits"] or 0 for c in courses)
    by_cat = {k: sum(c["credits"] or 0 for c in courses if c["category"] == k) for k in REQUIREMENTS}
    print(f"{len(courses)} courses, {total} credit hours (plan says 138). By category: {by_cat} vs {REQUIREMENTS}")
    for c in courses:
        flag = "  <-- REVIEW" if c["needs_review"] else ""
        print(f"  {c['term']:<10} {c['code']:<12} {c['credits']}  {c['name_en'][:38]:<38} pre={c['prereqs']}{flag}")


if __name__ == "__main__":
    main()
