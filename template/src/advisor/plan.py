"""
The course tracker: what a student has passed, what is left, and what they can take next.

Data: data/plans/computer_engineering.json, parsed from the official study-plan PDF by
scripts/parse_study_plan.py (every course keeps the PDF page it came from).

Prerequisites are stored as "AND of ORs": [["ENCS338", "ENCS2380"], ["ENEE2360"]] means
(ENCS338 or ENCS2380) and ENEE2360. A group whose courses are all outside this plan (old
codes, other departments) can't be checked from the student's ticks, so it is reported as
"check with your advisor" instead of blocking the course.

How this reaches the chat: student_context() writes a short Arabic summary that the answer
pipeline adds as one more SOURCE ("ملف الطالب"), cited like any document. The LLM still only
answers from sources, so personal answers stay grounded.
"""

import json
import re
from functools import lru_cache

from config import ROOT

PLANS_DIR = ROOT / "data" / "plans"
PROGRAMS = {"computer_engineering": "هندسة الحاسوب"}
COURSE_CODE = re.compile(r"\b[A-Za-z]{4}\s?\d{3,5}\b")
# Equivalent codes written in the plan itself (p. 9): "COMP2321 or COMP242 or COMP2421 or COMP23xx".
ALIASES = {"COMP23xx": {"COMP2321", "COMP242", "COMP2421"}}


def _expand(passed: set[str]) -> set[str]:
    out = set(passed)
    for code, same in ALIASES.items():
        if code in passed:
            out |= same
    return out


@lru_cache(maxsize=4)
def load_plan(program: str = "computer_engineering") -> dict:
    plan = json.loads((PLANS_DIR / f"{program}.json").read_text(encoding="utf-8"))
    plan["by_code"] = {c["code"]: c for c in plan["courses"]}
    return plan


def plan_available(program: str = "computer_engineering") -> bool:
    return (PLANS_DIR / f"{program}.json").exists()


def progress(plan: dict, passed: set[str]) -> dict:
    """Credit hours done per requirement category, and in total."""
    done = {k: 0 for k in plan["requirements"]}
    for c in plan["courses"]:
        if c["code"] in passed:
            done[c["category"]] += c["credits"] or 0
    total_done = sum(done.values())
    return {"done": done, "required": plan["requirements"], "total_done": total_done,
            "total": plan["total_hours"], "ratio": total_done / plan["total_hours"]}


def missing_prereqs(plan: dict, code: str, passed: set[str]) -> tuple[list[list[str]], list[list[str]]]:
    """(groups not yet satisfied, groups we can't check because none of their courses is in the plan)."""
    missing, unknown = [], []
    passed = _expand(passed)
    for group in plan["by_code"][code]["prereqs"]:
        if any(c in passed for c in group):
            continue
        known = set(plan["by_code"]) | {a for same in ALIASES.values() for a in same}
        if any(c in known for c in group):
            missing.append(group)
        else:
            unknown.append(group)
    return missing, unknown


def remaining(plan: dict, passed: set[str]) -> list[dict]:
    return [c for c in plan["courses"] if c["code"] not in passed]


def eligible_now(plan: dict, passed: set[str]) -> list[dict]:
    return [c for c in remaining(plan, passed) if not missing_prereqs(plan, c["code"], passed)[0]]


def codes_in(text: str) -> list[str]:
    return [m.replace(" ", "").upper() for m in COURSE_CODE.findall(text)]


def _course_line(c: dict) -> str:
    return f"{c['code']} {c['name_en']} ({c['credits']} س.م، {c['term']})"


def _or(group: list[str]) -> str:
    return " أو ".join(group)


def student_context(plan: dict, passed: set[str], question: str = "") -> str:
    """The student's record + plan facts, written as a source the LLM can cite."""
    p = progress(plan, passed)
    labels = plan["category_labels"]
    lines = [f"التخصص: {plan['program']} (الخطة الدراسية {plan['doc_title']})",
             f"الساعات المنجزة: {p['total_done']} من {p['total']} ساعة معتمدة، المتبقي {p['total'] - p['total_done']}.",
             "حسب نوع المتطلب: " + "، ".join(
                 f"{labels[k]} {p['done'][k]}/{p['required'][k]}" for k in plan["requirements"])]
    done = [c["code"] for c in plan["courses"] if c["code"] in passed]
    lines.append("المساقات التي أنهاها الطالب: " + ("، ".join(done) if done else "لا شيء بعد"))
    rest = remaining(plan, passed)
    lines.append("المساقات المتبقية في الخطة (" + str(len(rest)) + "): " + "؛ ".join(_course_line(c) for c in rest))
    lines.append("يستطيع تسجيلها الآن (متطلباتها السابقة منجزة): " +
                 ("؛ ".join(c["code"] for c in eligible_now(plan, passed)) or "لا شيء"))
    for code in codes_in(question):   # details for every course named in the question
        c = plan["by_code"].get(code)
        if not c:
            continue
        missing, unknown = missing_prereqs(plan, code, passed)
        pre = " و ".join(f"({_or(g)})" for g in c["prereqs"]) or "لا يوجد متطلب سابق مذكور في الخطة"
        status = "أنهاه الطالب" if code in passed else (
            "متطلباته السابقة منجزة" if not missing else "ينقصه: " + " و ".join(f"({_or(g)})" for g in missing))
        note = f"؛ يحتاج تأكيداً من المرشد: {' و '.join(_or(g) for g in unknown)}" if unknown else ""
        lines.append(f"المساق {_course_line(c)}: المتطلب السابق {pre} (ص {c['prereq_page'] or c['page']})؛ "
                     f"حالة الطالب: {status}{note}")
    return "\n".join(lines)


def course_facts_chunk(plan: dict, codes: list[str]) -> dict | None:
    """Exact lookup: course codes named in a question -> their rows from the 2026 plan (credits, term,
    prerequisites with page). Embeddings are weak on codes like ENCS3350 and the old 2024-25 guide
    has outdated descriptions, so the structured plan row is added as its own cited source."""
    rows = [plan["by_code"][c] for c in dict.fromkeys(codes) if c in plan["by_code"]]
    if not rows:
        return None
    lines = []
    for c in rows:
        pre = " و ".join(f"({_or(g)})" for g in c["prereqs"]) or "لا يوجد متطلب سابق مذكور"
        lines.append(f"{c['code']} {c['name_en']}: {c['credits']} ساعات معتمدة، موقعه في الخطة: "
                     f"{plan['term_labels'][c['term']]}، المتطلب السابق: {pre}.")
    pages = sorted({c["prereq_page"] or c["page"] for c in rows} | {rows[0]["page"]})
    return {
        "id": "plan-courses", "source": plan["source"], "doc_title": plan["doc_title"],
        "version": "2026", "date": "2026-04-25", "url": "", "kind": "plan", "category": "الخطط الدراسية",
        "section_title": "بيانات المساق من الخطة", "section_path": f"{plan['doc_title']} > جدول الخطة ووصف المساقات",
        "page_start": pages[0], "page_end": pages[-1], "part": 1, "parts": 1,
        "text": "\n".join(lines), "scores": {"rrf": 0, "cosine": 1.0, "bm25": 0},
    }


def as_source_chunk(plan: dict, passed: set[str], question: str) -> dict:
    """The student's profile shaped like a retrieved chunk, so prompts/citations/UI treat it the same."""
    pages = sorted({plan["by_code"][c]["prereq_page"] for c in codes_in(question)
                    if c in plan["by_code"] and plan["by_code"][c]["prereq_page"]} | set(plan["table_pages"]))
    return {
        "id": "student-profile", "source": plan["source"], "doc_title": "ملف الطالب",
        "version": "", "date": "", "url": "", "kind": "profile", "category": "ملف الطالب",
        "section_title": f"خطة {plan['program']}",
        "section_path": f"ملف الطالب > {plan['doc_title']}",
        "page_start": pages[0], "page_end": pages[-1],
        "part": 1, "parts": 1, "text": student_context(plan, passed, question),
        "scores": {"rrf": 0, "cosine": 1.0, "bm25": 0},
    }
