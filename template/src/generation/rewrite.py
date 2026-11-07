"""Query rewriting: dialect -> formal Arabic, follow-up -> standalone question (lesson D2)."""

from config import REWRITE_MODEL
from src.generation.llm import chat
from src.generation.prompts import rewrite_system_prompt

HISTORY_TURNS = 3


def rewrite_question(question: str, history: list[dict]) -> dict:
    recent = history[-HISTORY_TURNS * 2:]
    conversation = "\n".join(
        f"{'المستخدم' if m['role'] == 'user' else 'المساعد'}: {m['content'][:500]}" for m in recent)
    result = chat(REWRITE_MODEL, [
        {"role": "system", "content": rewrite_system_prompt()},
        {"role": "user", "content": f"المحادثة السابقة: {conversation or '(لا يوجد)'}\nالسؤال: {question}\nجملة البحث:"},
    ])
    result["text"] = result["text"].splitlines()[0].strip() if result["text"] else question
    return result
