"""
The ANSWERING phase, the whole pipeline for one question:

    question + chat history
        |  (6) rewrite: dialect -> formal Arabic, follow-up -> standalone question
        v
    search query
        |  (5) hybrid retrieval: vectors + BM25, fused with RRF -> top-k chunks
        v
    chunks + best similarity score
        |  (7) refusal gate: best score below threshold? -> refuse, don't call the LLM
        v
        |  (8) grounded generation: LLM answers ONLY from the chunks, with citations
        v
    answer + sources + debug info (shown in the UI's "how did I get this answer" panel)

Try it from the terminal:
    python -m src.generation.answer "كم سعر الساعة المعتمدة في كلية الهندسة؟"
"""

import sys
import time

from config import CHAT_MODEL, INDEX_DIR, REFUSAL_MESSAGE, REFUSAL_THRESHOLD, TOP_K
from src.generation.llm import chat
from src.generation.prompts import build_answer_messages
from src.generation.rewrite import rewrite_question
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.store import VectorStore


class RagPipeline:
    def __init__(self):
        self.retriever = HybridRetriever(VectorStore.load(INDEX_DIR))

    def answer(self, question: str, history: list[dict] | None = None,
               use_rewrite: bool = True, use_bm25: bool = True, top_k: int = TOP_K) -> dict:
        start = time.time()
        history = history or []
        tokens = {"input": 0, "output": 0}

        # (6) Rewrite the question into a clean, standalone search query.
        query = question
        if use_rewrite:
            rewritten = rewrite_question(question, history)
            query = rewritten["text"]
            _add_tokens(tokens, rewritten)

        # (5) Retrieve the most relevant chunks.
        retrieval = self.retriever.retrieve(query, top_k=top_k, use_bm25=use_bm25)

        # (7) Refusal gate: if nothing is even close in meaning, the documents
        # don't cover this question. Refuse now, with no LLM call and no chance to hallucinate.
        refused_by_gate = retrieval.best_dense_score < REFUSAL_THRESHOLD
        if refused_by_gate:
            answer_text = REFUSAL_MESSAGE
        else:
            # (8) Grounded generation.
            messages = build_answer_messages(question, query, retrieval.chunks)
            generated = chat(CHAT_MODEL, messages)
            answer_text = generated["text"]
            _add_tokens(tokens, generated)

        refused = refused_by_gate or "لم أجد هذه المعلومة" in answer_text
        return {
            "answer": answer_text,
            "refused": refused,
            "sources": [] if refused else retrieval.chunks,
            "debug": {
                "question": question,
                "search_query": query,
                "best_cosine": round(retrieval.best_dense_score, 3),
                "threshold": REFUSAL_THRESHOLD,
                "refused_by_gate": refused_by_gate,
                "retrieved": retrieval.chunks,
                "tokens": tokens,
                "seconds": round(time.time() - start, 2),
            },
        }


def _add_tokens(total: dict, result: dict) -> None:
    total["input"] += result["input_tokens"]
    total["output"] += result["output_tokens"]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "كم سعر الساعة المعتمدة في كلية الهندسة؟"
    result = RagPipeline().answer(question)
    d = result["debug"]
    print(f"Question:      {question}")
    print(f"Search query:  {d['search_query']}")
    print(f"Best cosine:   {d['best_cosine']}  (threshold {d['threshold']})")
    print("Retrieved:")
    for c in d["retrieved"]:
        print(f"   {c['source']} p{c['page']}  {c['scores']}")
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\n{d['seconds']}s, tokens {d['tokens']}")
