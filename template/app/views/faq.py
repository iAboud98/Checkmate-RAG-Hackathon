"""
The FAQ tab: common student questions answered AHEAD OF TIME by the same RAG pipeline
(scripts/build_faq.py -> data/faq.json), so they open instantly and still carry citations.
Below them: the live "most asked" list from the chat history (analytics).
"""

import json
from collections import Counter

import streamlit as st
from common import render_answer, show_sources

from config import ROOT
from src.ingest.normalize import normalize_arabic
from src.storage import db

FAQ_PATH = ROOT / "data" / "faq.json"


def _ask(question: str) -> None:
    st.session_state.pending = question
    st.session_state.conv_id = None
    st.session_state.goto_chat = True


def render() -> None:
    st.markdown("### ❓ الأسئلة الشائعة")
    st.caption("إجابات جاهزة من وثائق بيرزيت الرسمية، مع المصادر. اضغط \"اسأل المرشد\" لتكمل المحادثة.")
    if not FAQ_PATH.exists():
        st.info("لم تُولَّد الأسئلة الشائعة بعد: `python scripts/build_faq.py`")
        return
    faq = json.loads(FAQ_PATH.read_text(encoding="utf-8"))
    search = st.text_input("🔎 ابحث في الأسئلة", placeholder="مثال: إنذار، انسحاب، منح...")
    needle = normalize_arabic(search.strip())
    for topic, items in faq["topics"].items():
        shown = [it for it in items if not needle or needle in normalize_arabic(it["question"] + it["answer"])]
        if not shown:
            continue
        st.markdown(f"#### {topic}")
        for j, it in enumerate(shown):
            with st.expander(it["question"]):
                st.markdown(render_answer(it["answer"], it["sources"]), unsafe_allow_html=True)
                show_sources(it["sources"], it.get("cited"))
                st.button("♞ اسأل المرشد عن هذا", key=f"faq-{topic}-{j}", on_click=_ask, args=(it["question"],))

    answers = db.recent_answers()
    if answers:
        st.markdown("#### 🔥 الأكثر سؤالاً الآن")
        counts = Counter(normalize_arabic(a["search_query"] or a["question"]) for a in answers if not a["refused"])
        examples = {normalize_arabic(a["search_query"] or a["question"]): a["question"] for a in answers}
        for k, n in counts.most_common(5):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"• {examples[k]}  <span class='cm-badge'>{n}×</span>", unsafe_allow_html=True)
            c2.button("اسأل", key=f"hot-{k}", on_click=_ask, args=(examples[k],))
    st.caption(f"آخر توليد: {faq.get('generated_at', '')}")
