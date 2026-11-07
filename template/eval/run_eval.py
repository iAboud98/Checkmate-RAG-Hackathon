"""
Evaluation (5 rubric points + tie-break #2). Write eval/questions.jsonl BEFORE tuning.

Each line: {"id", "type", "question", "history"?: [...], "gold_answer",
            "gold_sources": [{"source": "file.pdf", "section": "part of the section title"} or {"source", "page"}],
            "expect_refusal": bool}

Metrics:
  Hit@k / Precision@k   retrieved sections vs gold (by section title or page)   [answerable questions]
  Refusal accuracy      refused exactly when expected                            [all questions]
  Correct / Faithful    LLM judge vs gold answer / vs retrieved text             [answerable questions]
  Cited                 answer contains a [file، section...] citation
  avg seconds / tokens

    python eval/run_eval.py                 full system
    python eval/run_eval.py --dense-only    no BM25        (before/after comparison)
    python eval/run_eval.py --no-rewrite    no rewriting   (before/after comparison)
    python eval/run_eval.py --calibrate     retrieval only: suggests REFUSAL_THRESHOLD (lesson D1)
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import JUDGE_MODEL, REFUSAL_THRESHOLD, TOP_K  # noqa: E402
from src.generation.answer import RagPipeline  # noqa: E402
from src.generation.llm import chat  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
CITATION = re.compile(r"\[[^\]]+\.(pdf|docx|md|txt)[^\]]*\]", re.IGNORECASE)

JUDGE_PROMPT = """أنت مُقيّم صارم لنظام أسئلة وأجوبة. ستعطى: السؤال، الإجابة المرجعية، إجابة النظام، والمقاطع التي اعتمد عليها النظام.
- correct: هل إجابة النظام تتفق مع الإجابة المرجعية في المعلومة الأساسية؟
- faithful: هل كل معلومة في إجابة النظام مدعومة بالمقاطع المرفقة؟
أجب بصيغة JSON فقط: {"correct": true/false, "faithful": true/false, "reason": "سبب قصير"}"""


def load_questions() -> list[dict]:
    with open(EVAL_DIR / "questions.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def matches_gold(chunk: dict, gold: dict) -> bool:
    if chunk["source"] != gold["source"]:
        return False
    if "section" in gold:
        return gold["section"] in chunk["section_title"] or gold["section"] in chunk["section_path"]
    if "page" in gold and chunk.get("page_start"):
        return chunk["page_start"] <= gold["page"] <= chunk["page_end"]
    return True


def judge(q: dict, answer: str, chunks: list[dict]) -> dict:
    context = "\n\n".join(f"[{c['citation']}]\n{c['text']}" for c in chunks) or "(لا يوجد)"
    result = chat(JUDGE_MODEL, [
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": f"السؤال: {q['question']}\n\nالإجابة المرجعية: {q['gold_answer']}\n\n"
                                    f"إجابة النظام: {answer}\n\nالمقاطع:\n{context}"},
    ])
    match = re.search(r"\{.*\}", result["text"], re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def calibrate(pipeline: RagPipeline) -> None:
    rows = []
    for q in load_questions():
        state = pipeline.prepare(q["question"], q.get("history", []))
        rows.append((q, state["retrieval"].best_dense_score, state["query"]))
        print(f"  {q['id']} {'OUT ' if q['expect_refusal'] else 'IN  '} cosine={state['retrieval'].best_dense_score:.3f}  {state['query']}")
    inside = [s for q, s, _ in rows if not q["expect_refusal"]]
    outside = [s for q, s, _ in rows if q["expect_refusal"]]
    lowest_in = min(inside) if inside else 0
    print(f"\nLowest in-scope cosine: {lowest_in:.3f}   out-of-scope: {', '.join(f'{s:.3f}' for s in outside)}")
    print(f"Current REFUSAL_THRESHOLD = {REFUSAL_THRESHOLD}")
    print(f"Suggested: about {max(0.0, lowest_in - 0.07):.2f} (safely below every in-scope question).")
    if outside and max(outside) >= lowest_in - 0.07:
        print("Some out-of-scope questions score like real ones. No threshold separates them; "
              "the prompt's refusal rule (layer 2) must catch those. Don't raise the threshold to block them.")


def evaluate(pipeline: RagPipeline, use_bm25: bool, use_rewrite: bool, label: str) -> None:
    rows = []
    for q in load_questions():
        r = pipeline.answer(q["question"], q.get("history", []), use_rewrite=use_rewrite, use_bm25=use_bm25)
        retrieved = r["debug"]["retrieved"]
        row = {"id": q["id"], "type": q["type"], "question": q["question"], "search_query": r["debug"]["search_query"],
               "answer": r["answer"], "refusal_ok": r["refused"] == q["expect_refusal"],
               "seconds": r["debug"]["seconds"], "tokens": sum(r["debug"]["tokens"].values()),
               "best_cosine": r["debug"]["best_cosine"], "retrieved": [c["citation"] for c in retrieved]}
        if q["gold_sources"]:
            hits = [any(matches_gold(c, g) for g in q["gold_sources"]) for c in retrieved]
            verdict = judge(q, r.get("answer_labeled", r["answer"]), r["sources"])
            row.update(hit=int(any(hits)), precision=sum(hits) / len(hits) if hits else 0.0,
                       cited=bool(r.get("cited")) or bool(CITATION.search(r["answer"])), correct=bool(verdict.get("correct")),
                       faithful=bool(verdict.get("faithful")), judge_reason=verdict.get("reason", ""))
        rows.append(row)
        print(f"  {q['id']} {q['type']:<13} refusal_ok={row['refusal_ok']!s:<5} hit={row.get('hit', '-')} "
              f"correct={row.get('correct', '-')!s:<5} {row['seconds']}s")

    answerable = [r for r in rows if "hit" in r]
    avg = lambda xs: round(sum(map(float, xs)) / len(xs), 3) if xs else 0.0  # noqa: E731
    summary = {"label": label, "bm25": use_bm25, "rewrite": use_rewrite, "top_k": TOP_K,
               f"hit@{TOP_K}": avg([r["hit"] for r in answerable]),
               f"precision@{TOP_K}": avg([r["precision"] for r in answerable]),
               "refusal_accuracy": avg([r["refusal_ok"] for r in rows]),
               "correct": avg([r["correct"] for r in answerable]),
               "faithful": avg([r["faithful"] for r in answerable]),
               "cited": avg([r["cited"] for r in answerable]),
               "avg_seconds": avg([r["seconds"] for r in rows]), "avg_tokens": avg([r["tokens"] for r in rows])}
    out = EVAL_DIR / "results" / f"{label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== {label} ===")
    for k, v in summary.items():
        print(f"  {k:<18} {v}")
    failures = [r for r in rows if not r["refusal_ok"] or r.get("hit") == 0 or r.get("correct") is False]
    if failures:
        print("\nFailures to analyse (put the worst one in the README and on a slide):")
        for r in failures:
            print(f"  {r['id']} {r['question']}\n     query: {r['search_query']}\n     answer: {r['answer'][:150]}")
    print(f"\nDetails: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dense-only", action="store_true")
    ap.add_argument("--no-rewrite", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    args = ap.parse_args()
    pipe = RagPipeline()
    if args.calibrate:
        calibrate(pipe)
    else:
        name = "_".join(n for n, on in (("dense_only", args.dense_only), ("no_rewrite", args.no_rewrite)) if on) or "full"
        evaluate(pipe, use_bm25=not args.dense_only, use_rewrite=not args.no_rewrite, label=name)
