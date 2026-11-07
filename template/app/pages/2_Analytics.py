"""Analytics: usage, refusal rate, speed, cost, most-asked and unanswered questions."""

from collections import Counter

import streamlit as st
from common import require_login, setup_page

from config import PRICE_INPUT_PER_1M, PRICE_OUTPUT_PER_1M
from src.ingest.normalize import normalize_arabic
from src.storage import db

setup_page("التحليلات")
require_login(role="admin")
st.title("📊 التحليلات")

s = db.stats()
if not s["answers"]:
    st.info("لا توجد أسئلة بعد.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("الأسئلة", s["answers"])
c2.metric("المحادثات / المستخدمون", f"{s['conversations']} / {s['users']}")
c3.metric("نسبة الرفض", f"{s['refusal_rate'] * 100:.0f}%")
c4.metric("متوسط الزمن", f"{s['avg_seconds']:.1f} s")

tokens = s["input_tokens"] + s["output_tokens"]
if PRICE_INPUT_PER_1M or PRICE_OUTPUT_PER_1M:
    cost = s["input_tokens"] / 1e6 * PRICE_INPUT_PER_1M + s["output_tokens"] / 1e6 * PRICE_OUTPUT_PER_1M
    st.caption(f"Tokens: {tokens:,} · estimated cost ${cost:.4f} · per answer ${cost / s['answers']:.5f}")
else:
    st.caption(f"Tokens: {tokens:,} ({tokens // s['answers']:,} per answer). Set PRICE_*_PER_1M in .env to see cost.")

st.subheader("الأسئلة يومياً")
st.bar_chart(db.questions_per_day(), x="day", y="questions")

answers = db.recent_answers()

st.subheader("الأكثر سؤالاً")
st.caption("مجمّعة حسب جملة البحث بعد إعادة الصياغة، فتجتمع الصيغ المختلفة للسؤال نفسه.")
counts = Counter(normalize_arabic(a["search_query"] or a["question"]) for a in answers)
examples = {normalize_arabic(a["search_query"] or a["question"]): a["question"] for a in answers}
st.dataframe([{"السؤال": examples[k], "العدد": n} for k, n in counts.most_common(10)], hide_index=True,
             use_container_width=True)

st.subheader("أسئلة بلا إجابة (فجوات في المحتوى)")
st.caption("ما يسأله المستخدمون ولا تغطيه المستندات: أضف وثائق تغطيه.")
refused = [{"السؤال": a["question"], "الوقت": a["created_at"]} for a in answers if a["refused"]]
st.dataframe(refused or [{"السؤال": "—", "الوقت": ""}], hide_index=True, use_container_width=True)
