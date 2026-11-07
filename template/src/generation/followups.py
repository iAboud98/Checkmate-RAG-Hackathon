"""
Follow-up questions under each answer (like Perplexity's "Related"), so students discover
what else the documents can answer.

One small, cheap call (the rewrite model) gets the question, the answer and the TITLES of the
retrieved sections, and must suggest questions those sections can answer. That keeps the
suggestions in scope: clicking one should lead to a grounded answer, not a refusal.
"""

import json

from config import REWRITE_MODEL
from src.generation.llm import chat

PROMPT = """أنت تساعد طالباً في جامعة بيرزيت. بناءً على سؤاله والإجابة وعناوين الأقسام المتاحة،
اقترح 3 أسئلة متابعة قصيرة (أقل من 12 كلمة) بالعربية، يمكن الإجابة عنها من هذه الأقسام نفسها.
لا تكرر السؤال الأصلي. أجب بصيغة JSON فقط: {"questions": ["...", "...", "..."]}"""


def suggest_followups(question: str, answer: str, chunks: list[dict]) -> tuple[list[str], dict]:
    titles = "\n".join(f"- {c['doc_title']} > {c['section_title']}" for c in chunks)
    result = chat(REWRITE_MODEL, [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": f"السؤال: {question}\nالإجابة: {answer[:1200]}\nالأقسام:\n{titles}"},
    ])
    try:
        text = result["text"]
        questions = json.loads(text[text.find("{"): text.rfind("}") + 1])["questions"]
        questions = [q.strip() for q in questions if isinstance(q, str) and q.strip()][:3]
    except (ValueError, KeyError, TypeError):
        questions = []
    return questions, {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}
