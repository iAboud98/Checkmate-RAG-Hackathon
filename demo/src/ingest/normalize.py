"""
MILESTONE 2: Arabic normalization.

The same Arabic word can be typed many ways:
    أحمد / احمد / إحمد        (different alef forms)
    مستشفى / مستشفي            (alef maqsura vs ya)
    مَدْرَسَة / مدرسة              (with or without diacritics)
    جـــامعة / جامعة            (tatweel stretching)

A computer sees these as DIFFERENT strings, so a keyword search for "احمد"
would miss "أحمد". Normalizing maps all variants to one form.

We apply it to BOTH the documents and the user's question, but only for
keyword search (BM25). The original text is kept for display and citations,
and the embedding model gets the original too (it already understands variants).
"""

import re

DIACRITICS = re.compile(r"[ً-ْٰ]")  # fatha, damma, kasra, shadda, sukun, tanween...
TATWEEL = "ـ"                                  # ـ


def normalize_arabic(text: str) -> str:
    text = DIACRITICS.sub("", text)
    text = text.replace(TATWEEL, "")
    text = re.sub("[إأآٱ]", "ا", text)   # all alef forms -> ا
    text = text.replace("ى", "ي")         # alef maqsura -> ya
    text = text.replace("ة", "ه")         # ta marbuta -> ha (people type both)
    text = text.replace("ؤ", "و").replace("ئ", "ي")
    return text.lower()                   # lowercases the Latin part, e.g. course codes


# Very common words that carry no meaning for search ("in", "from", "the"...).
STOPWORDS = {
    "في", "من", "على", "الي", "عن", "مع", "هذا", "هذه", "ذلك", "التي", "الذي",
    "او", "و", "ثم", "كل", "قد", "هو", "هي", "ما", "ماذا", "هل", "كم", "كيف",
    "لا", "ان", "اذا", "بعد", "قبل", "عند", "بين", "لكل", "لها", "له",
}


def tokenize(text: str) -> list[str]:
    """Normalize, split into words, drop stopwords and the definite article ال."""
    words = re.findall(r"\w+", normalize_arabic(text))
    tokens = []
    for w in words:
        if w.startswith("ال") and len(w) > 4:   # "المساق" -> "مساق"
            w = w[2:]
        if w not in STOPWORDS:
            tokens.append(w)
    return tokens
