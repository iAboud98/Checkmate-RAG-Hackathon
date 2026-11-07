"""
Text cleanup shared by all loaders, plus the Arabic heading patterns.
Each fix here comes from a real problem in docs/LESSONS_LEARNED.md.
"""

import re
from collections import Counter

BIDI_MARKS = re.compile("[‎‏‪-‮⁦-⁩]")   # invisible direction marks (lesson C1b)

# Arabic document structure: "الباب الأول", "الفصل 2", "المادة 5:", "البند 3", "أولاً:", "1.2 ...", "أ) ..."
# Rank = how high in the hierarchy (used only when a heading has no font/style information).
HEADING_PATTERNS = [
    (1, re.compile(r"^(الباب|الجزء)\s+\S+")),
    (2, re.compile(r"^(الفصل)\s+\S+")),
    (3, re.compile(r"^(القسم)\s+\S+")),
    (4, re.compile(r"^(المادة|مادة|البند)\s*[\(\[]?\s*[\d٠-٩]+|^(المادة|البند)\s+(الأولى|الثانية|الثالثة|الرابعة|الخامسة|السادسة|السابعة|الثامنة|التاسعة|العاشرة)"
                    # ordinals past ten ("المادة الحادية عشرة:", "المادة العشرون:"), colon required
                    r"|^(المادة|البند)\s+ال[^\s:]+(\s+(عشرة|عشر|والعشرون|والثلاثون|والأربعون))?\s*:")),
    (5, re.compile(r"^(أولا|ثانيا|ثالثا|رابعا|خامسا|سادسا|سابعا|ثامنا|تاسعا|عاشرا)ً?\s*[:\-–.]")),
]
MAX_HEADING_CHARS = 90   # a "heading" longer than this is really a paragraph

# Start of a numbered clause inside a section ("1. ...", "٢- ...", "أ) ...", "أولاً: ...").
CLAUSE_START = re.compile(r"^\s*([\d٠-٩]+\s*[.)\-–]|[أ-ي]\s*[)\-–]|(أولا|ثانيا|ثالثا|رابعا|خامسا)ً?\s*[:\-–])")


def regex_heading_rank(line: str) -> int | None:
    """Return the hierarchy rank if the line looks like an Arabic structural heading, else None."""
    line = line.strip()
    if not line or len(line) > MAX_HEADING_CHARS:
        return None
    for rank, pattern in HEADING_PATTERNS:
        if pattern.match(line):
            return rank
    return None


# Lam-alef ligature read back in the wrong order (lesson A1): "الأكاديمي" extracts as "األكاديمي".
# Only fixes that are always safe: "األ/اإل/اآل" never occur in correct Arabic, and a lone "ال"
# between spaces is always the broken word "لا". Ambiguous cases ("عالمة" vs the real word "عالم")
# are left alone; normalize_arabic() makes BM25 match them anyway.
LAM_ALEF_FIXES = [
    (re.compile("ا([أإآ])ل"), r"ال\1"),
    (re.compile(r"(^|\s)ال(?=\s|$|[.,:،])"), r"\1لا"),
]


def fix_lam_alef(line: str) -> str:
    for pattern, repl in LAM_ALEF_FIXES:
        line = pattern.sub(repl, line)
    return line


def tidy(line: str) -> str:
    """Leftovers of RTL visual ordering in PDFs (lessons A1, A2, A5)."""
    line = fix_lam_alef(BIDI_MARKS.sub("", line))
    line = re.sub(r"\s+([.,:،؛])", r"\1", line)          # "النهائي ." -> "النهائي."
    line = re.sub(r"%(\d+)", r"\1%", line)                # "%15" -> "15%"
    line = re.sub(r"(\d+)\(\s*\)", r"(\1)", line)         # "المادة 1( ):" -> "المادة (1):"
    line = re.sub(r"\)(\d+)\(", r"(\1)", line)            # ")1(" -> "(1)"
    line = re.sub(r"^([.،,])\s*(?=\S)", "", line)         # stray punctuation pushed to the line start
    line = re.sub(r"([^\d\s.])\.(\d+)$", r"\1 \2.", line)  # "الثاني.2025" at line end -> "الثاني 2025."
    return re.sub(r"\s{2,}", " ", line).strip()


def find_repeated_lines(pages_lines: list[list[str]], min_ratio: float = 0.5) -> set[str]:
    """
    Lines that repeat on many pages are headers/footers (lesson A6). Digits are masked so
    "صفحة 3 من 10" and "صفحة 4 من 10" count as the same line.
    Only the first/last 3 lines of each page are considered, where headers/footers live.
    """
    if len(pages_lines) < 2:
        return set()
    counts = Counter()
    for lines in pages_lines:
        edge = lines[:3] + lines[-3:]
        counts.update({_mask_digits(l) for l in edge if l.strip()})
    threshold = max(2, int(len(pages_lines) * min_ratio + 0.5))
    return {line for line, n in counts.items() if n >= threshold}


def is_repeated(line: str, repeated: set[str]) -> bool:
    return _mask_digits(line) in repeated


def _mask_digits(line: str) -> str:
    return re.sub(r"[\d٠-٩]+", "#", line.strip())


# Lesson A1: the lam-alef ligature (لا) often extracts as "ال" in the wrong order.
# These patterns almost never appear in correct Arabic text.
_LAM_ALEF_BROKEN = re.compile(r"(^|\s)(اال|اإل|األ|اآل)|عالمة|(^|\s)ال(\s|$)")


def lam_alef_suspicion(text: str) -> int:
    """Count suspicious lam-alef patterns. More than a handful per document = extraction is broken."""
    return len(_LAM_ALEF_BROKEN.findall(text))
