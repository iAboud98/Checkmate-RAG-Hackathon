"""
MILESTONE 6: Query rewriting, which fixes the question before we search.

Two problems, one cheap LLM call:

1. Dialect. Students ask "قديش بقدر أغيب؟" but the documents say
   "نسبة الغياب المسموحة". BM25 finds no shared words, and even embeddings do
   better with formal Arabic. Rewritten: "ما هي نسبة الغياب المسموح بها للطالب؟"

2. Follow-up questions. In a chat, the 2nd question often depends on the 1st:
       Q1: ما هو المتطلب السابق لمساق أنظمة التشغيل؟
       Q2: وكم ساعة معتمدة له؟        <- "له" = who? Searching this alone finds nothing.
   Rewritten using the history: "كم عدد الساعات المعتمدة لمساق أنظمة التشغيل؟"

We search with the rewritten question, but still show the model the original.
"""

from config import REWRITE_MODEL
from src.generation.llm import chat
from src.generation.prompts import REWRITE_SYSTEM_PROMPT

HISTORY_TURNS = 3  # how many previous question/answer pairs to consider


def rewrite_question(question: str, history: list[dict]) -> dict:
    recent = history[-HISTORY_TURNS * 2:]
    conversation = "\n".join(
        f"{'الطالب' if m['role'] == 'user' else 'المساعد'}: {m['content']}" for m in recent
    )
    user_message = (
        f"المحادثة السابقة:\n{conversation or '(لا يوجد)'}\n\n"
        f"سؤال الطالب الأخير: {question}"
    )
    result = chat(REWRITE_MODEL, [
        {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ])
    result["text"] = result["text"] or question  # never search with an empty string
    return result
