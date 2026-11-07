"""
Source guide for the Sources tab (like NotebookLM's per-source summary):

    python scripts/build_source_guide.py      ->  data/source_guide.json

For each document: a 2-sentence Arabic overview + up to 4 key topics, written by the small
model from the document's OWN first sections (about 3,000 characters). Shown in the UI as
"ملخص آلي" (automatic summary); answers never use it, they use the documents themselves.
Runs in parallel threads; re-running skips documents already summarized.
"""

import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DOCS_DIR, INDEX_DIR, REWRITE_MODEL, ROOT  # noqa: E402
from src.generation.llm import chat  # noqa: E402

OUT = ROOT / "data" / "source_guide.json"
PROMPT = """لخّص الوثيقة التالية من جامعة بيرزيت لطالب جامعي، اعتماداً على النص المرفق فقط.
أجب بصيغة JSON فقط: {"overview": "جملتان قصيرتان: ماذا تنظم الوثيقة ولمن", "topics": ["موضوع", "موضوع", "موضوع"]}
المواضيع: 3 إلى 4 كلمات مفتاحية قصيرة."""


def summarize(item: tuple[str, str, str]) -> tuple[str, dict]:
    file, title, text = item
    result = chat(REWRITE_MODEL, [{"role": "system", "content": PROMPT},
                                  {"role": "user", "content": f"العنوان: {title}\n\n{text[:3000]}"}])
    raw = result["text"]
    try:
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        return file, {"overview": str(data.get("overview", "")).strip(),
                      "topics": [str(t) for t in data.get("topics", [])][:4]}
    except ValueError:
        return file, {"overview": "", "topics": []}


def main() -> None:
    meta = json.loads((DOCS_DIR / "metadata.json").read_text(encoding="utf-8"))
    texts = defaultdict(str)
    with open(INDEX_DIR / "chunks.jsonl", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            if len(texts[c["source"]]) < 3000:
                texts[c["source"]] += f"\n## {c['section_title']}\n{c['text']}"
    guide = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    todo = [(f, m["title"], texts[f]) for f, m in meta.items() if f in texts and not guide.get(f, {}).get("overview")]
    print(f"Summarizing {len(todo)} documents...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        for file, entry in pool.map(summarize, todo):
            guide[file] = entry
            print(f"  {meta[file]['title'][:60]}: {entry['overview'][:70]}")
    OUT.write_text(json.dumps(guide, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(guide)} overviews to {OUT}")


if __name__ == "__main__":
    main()
