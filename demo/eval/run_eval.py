"""
MILESTONE 10: Evaluation, i.e. measuring the system instead of guessing.

For every question in eval/questions.jsonl we run the full pipeline and measure:

  Retrieval (did we find the right page?)  - only for questions that HAVE an answer
    Hit@k        1 if at least one retrieved chunk comes from a gold page, else 0
    Precision@k  fraction of the k retrieved chunks that come from a gold page

  Answer (was the final answer good?)
    Refusal accuracy  refused exactly when it should (out-of-scope) and answered otherwise
    Correct           an LLM judge compares the answer to the gold answer
    Faithful          an LLM judge checks every claim is supported by the retrieved chunks
    Cited             the answer contains at least one [file، ص N] citation

  Cost/speed: average seconds and tokens per question

Run from the demo/ folder:
    python eval/run_eval.py                    # full system
    python eval/run_eval.py --dense-only       # turn off BM25 -> compare
    python eval/run_eval.py --no-rewrite       # turn off query rewriting -> compare
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CHAT_MODEL, TOP_K  # noqa: E402
from src.generation.answer import RagPipeline  # noqa: E402
from src.generation.llm import chat  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
CITATION = re.compile(r"\[[^\]]*ص\s*\d+[^\]]*\]")

JUDGE_PROMPT = """أنت مُقيّم صارم لنظام أسئلة وأجوبة. ستعطى: السؤال، الإجابة المرجعية، إجابة النظام، والمقاطع التي اعتمد عليها النظام.
قيّم أمرين:
- correct: هل إجابة النظام تتفق مع الإجابة المرجعية في المعلومة الأساسية؟
- faithful: هل كل معلومة في إجابة النظام مدعومة بالمقاطع المرفقة (لا شيء مخترع من خارجها)؟
أجب بصيغة JSON فقط: {"correct": true/false, "faithful": true/false, "reason": "سبب قصير"}"""


def judge(question: str, gold: str, answer: str, chunks: list[dict]) -> dict:
    context = "\n\n".join(f"[{c['source']}، ص {c['page']}]\n{c['text']}" for c in chunks) or "(لا يوجد)"
    result = chat(CHAT_MODEL, [
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": f"السؤال: {question}\n\nالإجابة المرجعية: {gold}\n\nإجابة النظام: {answer}\n\nالمقاطع:\n{context}"},
    ])
    match = re.search(r"\{.*\}", result["text"], re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def evaluate(use_bm25: bool, use_rewrite: bool, label: str) -> dict:
    questions = [json.loads(line) for line in open(EVAL_DIR / "questions.jsonl", encoding="utf-8") if line.strip()]
    pipeline = RagPipeline()
    rows = []

    for q in questions:
        result = pipeline.answer(q["question"], q.get("history", []), use_rewrite=use_rewrite, use_bm25=use_bm25)
        retrieved = result["debug"]["retrieved"]
        gold_pages = {(g["source"], g["page"]) for g in q["gold_sources"]}
        row = {
            "id": q["id"], "type": q["type"], "question": q["question"],
            "search_query": result["debug"]["search_query"],
            "answer": result["answer"],
            "refusal_ok": result["refused"] == q["expect_refusal"],
            "seconds": result["debug"]["seconds"],
            "tokens": result["debug"]["tokens"]["input"] + result["debug"]["tokens"]["output"],
            "best_cosine": result["debug"]["best_cosine"],
        }
        if gold_pages:  # retrieval metrics only make sense when an answer exists
            matches = [(c["source"], c["page"]) in gold_pages for c in retrieved]
            row["hit"] = int(any(matches))
            row["precision"] = sum(matches) / len(retrieved) if retrieved else 0.0
            row["cited"] = bool(CITATION.search(result["answer"]))
            verdict = judge(q["question"], q["gold_answer"], result["answer"], result["sources"])
            row["correct"] = bool(verdict.get("correct"))
            row["faithful"] = bool(verdict.get("faithful"))
            row["judge_reason"] = verdict.get("reason", "")
        rows.append(row)
        print(f"  {q['id']} {q['type']:<12} refusal_ok={row['refusal_ok']!s:<5} "
              f"hit={row.get('hit', '-')} correct={row.get('correct', '-')} cosine={row['best_cosine']}")

    answerable = [r for r in rows if "hit" in r]
    summary = {
        "label": label, "use_bm25": use_bm25, "use_rewrite": use_rewrite, "top_k": TOP_K,
        f"hit@{TOP_K}": _avg(r["hit"] for r in answerable),
        f"precision@{TOP_K}": _avg(r["precision"] for r in answerable),
        "refusal_accuracy": _avg(r["refusal_ok"] for r in rows),
        "correct": _avg(r["correct"] for r in answerable),
        "faithful": _avg(r["faithful"] for r in answerable),
        "cited": _avg(r["cited"] for r in answerable),
        "avg_seconds": _avg(r["seconds"] for r in rows),
        "avg_tokens": _avg(r["tokens"] for r in rows),
    }
    out = EVAL_DIR / "results" / f"{label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== Summary:", label, "===")
    for key, value in summary.items():
        print(f"  {key:<18} {value}")
    print(f"\nDetails saved to {out}")
    return summary


def _avg(values) -> float:
    values = [float(v) for v in values]
    return round(sum(values) / len(values), 3) if values else 0.0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dense-only", action="store_true", help="vectors only, no BM25")
    parser.add_argument("--no-rewrite", action="store_true", help="search with the raw question")
    args = parser.parse_args()
    label = "full" if not (args.dense_only or args.no_rewrite) else \
        "_".join(x for x, on in (("dense_only", args.dense_only), ("no_rewrite", args.no_rewrite)) if on)
    evaluate(use_bm25=not args.dense_only, use_rewrite=not args.no_rewrite, label=label)
