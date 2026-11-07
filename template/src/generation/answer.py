"""
The answering pipeline, in two halves so the UI can stream:

    prepare()  rewrite -> hybrid retrieve -> (+ student profile) -> refusal gate   (fast, no answer yet)
    stream()   grounded generation, yielding text as it arrives    (skipped if the gate refused)
    finish()   package answer + sources + debug info

answer() runs all three at once (used by the CLI and the eval):
    python -m src.generation.answer "كم يوم إجازة سنوية بستحق؟"
"""

import re
import sys
import time
from collections.abc import Iterator

import domain
from config import CHAT_MODEL, INDEX_DIR, REFUSAL_THRESHOLD, TOP_K
from src.generation.llm import chat_stream
from src.generation.prompts import build_answer_messages
from src.generation.rewrite import rewrite_question
from src.ingest.sections import citation_label
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.store import VectorStore
from src.advisor import plan as advisor

CITE = re.compile(r"\[(\d+)\]")


def is_plan_question(question: str) -> bool:
    """A question about the student's own plan: names a course code, or uses a "my plan" word."""
    return bool(advisor.codes_in(question)) or any(k in question for k in domain.PLAN_KEYWORDS)


class RagPipeline:
    def __init__(self):
        self.retriever = HybridRetriever(VectorStore.load(INDEX_DIR))

    def prepare(self, question: str, history: list[dict] | None = None,
                use_rewrite: bool = True, use_bm25: bool = True, top_k: int = TOP_K,
                student: dict | None = None) -> dict:
        """student = {"program": "computer_engineering", "passed": {...codes}} or None."""
        state = {"question": question, "start": time.time(), "tokens": {"input": 0, "output": 0}}
        query = question
        if use_rewrite:
            rewritten = rewrite_question(question, history or [])
            query = rewritten["text"]
            _add(state["tokens"], rewritten)
        retrieval = self.retriever.retrieve(query, top_k=top_k, use_bm25=use_bm25)
        chunks = list(retrieval.chunks)
        # Personal question + a known study plan: the student's profile becomes source [1].
        # It is a grounded source (official plan + the student's own ticks), so the score gate
        # must not refuse it; the prompt's refusal rule still applies.
        personal = bool(student) and is_plan_question(f"{question} {query}") \
            and advisor.plan_available(student["program"])
        if personal:
            plan = advisor.load_plan(student["program"])
            chunks.insert(0, advisor.as_source_chunk(plan, set(student["passed"]), f"{question} {query}"))
        # Exact lookup: a course code in the question -> that course's row from the newest plan.
        facts = None
        if not personal and advisor.plan_available():
            facts = advisor.course_facts_chunk(advisor.load_plan(), advisor.codes_in(f"{question} {query}"))
            if facts:
                chunks.insert(0, facts)
        state.update(query=query, retrieval=retrieval, chunks=chunks, personal=personal,
                     refused_by_gate=retrieval.best_dense_score < REFUSAL_THRESHOLD and not personal and not facts)
        return state

    def stream(self, state: dict) -> Iterator[str]:
        if state["refused_by_gate"]:   # layer 1 of refusal: nothing relevant, don't call the LLM
            yield domain.REFUSAL_MESSAGE
            return
        usage = {}
        messages = build_answer_messages(state["question"], state["query"], state["chunks"])
        yield from chat_stream(CHAT_MODEL, messages, usage)
        _add(state["tokens"], usage)

    def finish(self, state: dict, answer_text: str) -> dict:
        refused = state["refused_by_gate"] or domain.REFUSAL_MESSAGE[:20] in answer_text
        chunks = state["chunks"]
        for n, c in enumerate(chunks, start=1):
            c["n"] = n
            c["citation"] = citation_label(c)
        answer_text = answer_text.strip()
        cited = {int(m) for m in CITE.findall(answer_text) if 0 < int(m) <= len(chunks)}
        # Same answer with [n] expanded to the full label: used by the eval judge and the "Cited" check.
        labeled = CITE.sub(lambda m: f"[{chunks[int(m.group(1)) - 1]['citation']}]"
                           if 0 < int(m.group(1)) <= len(chunks) else m.group(0), answer_text)
        return {
            "answer": answer_text,
            "answer_labeled": labeled,
            "cited": sorted(cited),
            "refused": refused,
            "personal": state.get("personal", False),
            "sources": [] if refused else chunks,
            "debug": {
                "question": state["question"],
                "search_query": state["query"],
                "best_cosine": round(state["retrieval"].best_dense_score, 3),
                "threshold": REFUSAL_THRESHOLD,
                "refused_by_gate": state["refused_by_gate"],
                "retrieved": chunks,
                "tokens": state["tokens"],
                "seconds": round(time.time() - state["start"], 2),
            },
        }

    def answer(self, question: str, history: list[dict] | None = None, **options) -> dict:
        state = self.prepare(question, history, **options)
        return self.finish(state, "".join(self.stream(state)))


def _add(total: dict, usage: dict) -> None:
    total["input"] += usage.get("input_tokens", 0)
    total["output"] += usage.get("output_tokens", 0)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or domain.EXAMPLE_QUESTIONS[0]
    r = RagPipeline().answer(q)
    d = r["debug"]
    print(f"Question:     {q}\nSearch query: {d['search_query']}\nBest cosine:  {d['best_cosine']} (threshold {d['threshold']})")
    for c in d["retrieved"]:
        print(f"   [{c['citation']}]  {c['scores']}")
    print(f"\n{r['answer']}\n\n{d['seconds']}s, tokens {d['tokens']}")
