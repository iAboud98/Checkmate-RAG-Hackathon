"""
The course tracker card ("مساري الدراسي") next to the chat.

The student ticks the courses they passed (saved per user in SQLite). The card shows hours per
requirement type and what they can register now; the chat receives {"program", "passed"} and
adds the student's profile as a cited source for personal questions ("شو ضايلي؟").
"""

import html

import streamlit as st

from src.advisor import plan as advisor
from src.storage import db

PROGRAM = "computer_engineering"


@st.dialog("✏️ مساقاتي المنجزة · هندسة الحاسوب", width="large")
def _edit(user: dict, plan: dict, passed: set[str]) -> None:
    st.caption(f"من {plan['doc_title']} (ص {plan['table_pages'][0]}-{plan['table_pages'][-1]}). علّم ما أنهيته بنجاح.")
    chosen = set()
    for term in plan["terms"]:
        courses = [c for c in plan["courses"] if c["term"] == term]
        if not courses:
            continue
        st.markdown(f"**{plan['term_labels'][term]}**")
        cols = st.columns(3)
        for i, c in enumerate(courses):
            label = f"{c['code']} · {c['name_en']} ({c['credits']})"
            if cols[i % 3].checkbox(label, value=c["code"] in passed, key=f"pc-{c['code']}"):
                chosen.add(c["code"])
    if st.button("💾 حفظ", type="primary", use_container_width=True):
        db.set_passed(user["username"], PROGRAM, chosen)
        st.rerun()


def render(user: dict) -> dict | None:
    """Draw the card; return the student context for the pipeline (None = don't use the plan)."""
    if not advisor.plan_available(PROGRAM):
        return None
    plan = advisor.load_plan(PROGRAM)
    passed = db.get_passed(user["username"], PROGRAM)
    p = advisor.progress(plan, passed)
    with st.container(border=True):
        st.markdown("#### 🎓 مساري الدراسي")
        st.selectbox("التخصص", ["هندسة الحاسوب (خطة 2026)"], label_visibility="collapsed",
                     help="مدعوم حالياً: هندسة الحاسوب. بقية الخطط مفهرسة للبحث فقط.")
        st.progress(min(p["ratio"], 1.0), text=f"{p['total_done']} / {p['total']} ساعة معتمدة")
        for key, required in p["required"].items():
            done = p["done"][key]
            st.markdown(f'<div class="cm-muted">{plan["category_labels"][key]}: <b>{done}</b> / {required}</div>',
                        unsafe_allow_html=True)
        eligible = [c for c in advisor.eligible_now(plan, passed) if c["category"] == "required"][:10]
        if eligible:
            st.markdown("**تستطيع تسجيلها الآن:**")
            st.markdown(" ".join(f'<span class="cm-badge code" title="{html.escape(c["name_en"])}">{c["code"]}</span>'
                                 for c in eligible), unsafe_allow_html=True)
        if st.button("✏️ تعديل مساقاتي", use_container_width=True):
            _edit(user, plan, passed)
        use = st.toggle("استخدم خطتي في الإجابات", value=True,
                        help="يضيف ملفك الدراسي كمصدر عند الأسئلة الشخصية مثل: شو ضايلي؟ بقدر آخذ ENCS3350؟")
    return {"program": PROGRAM, "passed": passed} if use else None
