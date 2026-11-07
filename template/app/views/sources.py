"""
The Sources tab: every indexed document with an overview, so students (and judges) can see
exactly what the assistant knows, and what it doesn't.

Per document: title, category, version, pages covered, number of sections, Ritaj link, an AI
overview (scripts/build_source_guide.py, labelled "ملخص آلي") and its section list.
"""

import html
import json
from collections import defaultdict

import streamlit as st

from config import DOCS_DIR, INDEX_DIR, ROOT
from src.ingest.normalize import normalize_arabic

GUIDE_PATH = ROOT / "data" / "source_guide.json"
KIND_LABELS = {"regulation": "نظام / تعليمات", "guide": "دليل", "plan": "خطة دراسية", "decision": "قرار وزاري"}


@st.cache_data(show_spinner=False)
def _load(index_mtime: float) -> tuple[dict, dict, dict]:
    meta = json.loads((DOCS_DIR / "metadata.json").read_text(encoding="utf-8"))
    sections, pages = defaultdict(list), defaultdict(set)
    with open(INDEX_DIR / "chunks.jsonl", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            if c["part"] == 1:
                sections[c["source"]].append(c["section_title"])
            for p in (c.get("page_start"), c.get("page_end")):
                if p:
                    pages[c["source"]].add(p)
    guide = json.loads(GUIDE_PATH.read_text(encoding="utf-8")) if GUIDE_PATH.exists() else {}
    return meta, {"sections": dict(sections), "pages": {k: (min(v), max(v)) for k, v in pages.items()}}, guide


def render() -> None:
    meta, stats, guide = _load((INDEX_DIR / "chunks.jsonl").stat().st_mtime)
    st.markdown("### 📚 المصادر")
    st.caption(f"{len(meta)} وثيقة رسمية مفهرسة. كل إجابة تستشهد بإحداها مع رقم الصفحة؛ ما ليس هنا يُرفض.")

    c1, c2 = st.columns([2, 3])
    query = c1.text_input("🔎 ابحث عن وثيقة", placeholder="مثال: البكالوريوس، السكن، الذكاء الاصطناعي")
    kinds = c2.pills("النوع", list(KIND_LABELS.values()), selection_mode="multi", default=None)
    needle = normalize_arabic(query.strip())

    order = {"guide": 0, "plan": 1, "decision": 3, "regulation": 2}
    docs = sorted(meta.items(), key=lambda kv: (order.get(kv[1].get("kind"), 9), kv[1]["title"]))
    shown = [(f, m) for f, m in docs
             if (not kinds or KIND_LABELS.get(m.get("kind"), "") in kinds)
             and (not needle or needle in normalize_arabic(m["title"] + guide.get(f, {}).get("overview", "")))]
    st.markdown(f'<span class="cm-muted">{len(shown)} نتيجة</span>', unsafe_allow_html=True)

    cols = st.columns(2, gap="medium")
    for i, (file, m) in enumerate(shown):
        g = guide.get(file, {})
        secs = stats["sections"].get(file, [])
        pr = stats["pages"].get(file)
        badges = [f'<span class="cm-badge">{KIND_LABELS.get(m.get("kind"), "وثيقة")}</span>']
        if m.get("category"):
            badges.append(f'<span class="cm-badge">{html.escape(m["category"])}</span>')
        if m.get("version"):
            badges.append(f'<span class="cm-badge gold">إصدار {html.escape(m["version"])}</span>')
        link = f' · <a href="{html.escape(m["url"])}" target="_blank">رتاج ↗</a>' if m.get("url") else ""
        pages = f"ص {pr[0]}–{pr[1]}" if pr else "بدون صفحات"
        overview = html.escape(g.get("overview", "")) or '<span class="cm-muted">لا يوجد ملخص بعد.</span>'
        topics = "".join(f'<span class="cm-badge">{html.escape(t)}</span>' for t in g.get("topics", []))
        with cols[i % 2]:
            st.markdown(f"""<div class="cm-card"><h4>{html.escape(m['title'])}</h4>
                {''.join(badges)}<div class="cm-muted">{len(secs)} قسم · {pages}{link}</div>
                <p style="margin:8px 0 4px 0">{overview}</p>{topics}
                <div class="cm-muted" style="margin-top:4px">ملخص آلي من نص الوثيقة · للتفاصيل اسأل المرشد</div>
                </div>""", unsafe_allow_html=True)
            if secs:
                with st.expander(f"الأقسام ({len(secs)})"):
                    st.markdown("\n".join(f"- {s}" for s in secs[:80]) + ("\n- …" if len(secs) > 80 else ""))
