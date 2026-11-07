"""
Pre-answer the FAQ (domain.FAQ_QUESTIONS) with the real RAG pipeline:

    python scripts/build_faq.py      ->  data/faq.json

Same rewrite -> hybrid retrieval -> grounded answer -> citations as the chat, so every FAQ answer
has [n] sources with pages. Refused questions are left out (they'd show a content gap, not an
answer). Review the file by eye before the demo.
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import domain  # noqa: E402
from config import ROOT  # noqa: E402
from src.generation.answer import RagPipeline  # noqa: E402

OUT = ROOT / "data" / "faq.json"
KEEP = ("n", "citation", "doc_title", "section_title", "section_path", "page_start", "page_end", "url", "kind", "text")


def main() -> None:
    pipeline = RagPipeline()
    jobs = [(topic, q) for topic, qs in domain.FAQ_QUESTIONS.items() for q in qs]

    def run(job):
        topic, q = job
        return topic, q, pipeline.answer(q)

    topics = {t: [] for t in domain.FAQ_QUESTIONS}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for topic, q, r in pool.map(run, jobs):
            status = "REFUSED" if r["refused"] else f"{len(r['cited'])} cited"
            print(f"  [{status}] {q}")
            if not r["refused"]:
                topics[topic].append({"question": q, "answer": r["answer"], "cited": r["cited"],
                                      "sources": [{k: s.get(k) for k in KEEP} for s in r["sources"]]})
    faq = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "topics": {t: v for t, v in topics.items() if v}}
    OUT.write_text(json.dumps(faq, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {sum(len(v) for v in faq['topics'].values())} FAQ answers to {OUT}")


if __name__ == "__main__":
    main()
