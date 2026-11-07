"""
The المرشد tab: the RAG chat (left/right in RTL) + the student's course tracker.

Flow per question (lesson E1: the input is DISABLED while an answer is being written):
  1. chat_input / example / follow-up button -> session_state["pending"] -> rerun
  2. on the rerun: run prepare() (with the student's plan if the toggle is on), STREAM the answer
  3. finish() + follow-up suggestions -> save to SQLite -> clear pending -> rerun
"""

import streamlit as st
from common import load_pipeline, render_answer, show_sources

import domain
from src.generation.followups import suggest_followups
from src.storage import db
from views import tracker


def _sidebar(user: dict) -> tuple[bool, bool]:
    with st.sidebar:
        if st.button("➕ محادثة جديدة", use_container_width=True):
            st.session_state.conv_id = None
            st.rerun()
        st.subheader("المحادثات السابقة")
        for conv in db.list_conversations(user["username"]):
            label = ("▶ " if conv["id"] == st.session_state.conv_id else "") + conv["title"]
            if st.button(label, key=conv["id"], use_container_width=True):
                st.session_state.conv_id = conv["id"]
                st.rerun()
        with st.expander("⚙️ إعدادات للتجربة"):
            use_rewrite = st.toggle("إعادة صياغة السؤال", value=True)
            use_bm25 = st.toggle("البحث الهجين", value=True)
    return use_rewrite, use_bm25


def _details(details: dict, last: bool, key: str) -> None:
    show_sources(details.get("sources") or [], details.get("cited"))
    d = details["debug"]
    with st.expander("🔍 كيف وصلت للإجابة؟"):
        st.markdown(f"**جملة البحث:** {d['search_query']}")
        gate = "❌ رفض قبل استدعاء النموذج" if d["refused_by_gate"] else "✅ تجاوز العتبة"
        st.markdown(f"**أعلى تشابه:** `{d['best_cosine']}` (العتبة `{d['threshold']}`) → {gate}")
        if details.get("personal"):
            st.markdown("**🎓 استُخدم ملفك الدراسي كمصدر [1]**")
        st.dataframe([{"#": s.get("n"), "citation": s["citation"], **(s.get("scores") or {})}
                      for s in details["retrieved"]], hide_index=True)
        st.caption(f"⏱️ {d['seconds']} s · tokens {d['tokens']['input']} in / {d['tokens']['output']} out")
    if last and details.get("followups"):
        st.markdown('<span class="cm-muted">أسئلة ذات صلة:</span>', unsafe_allow_html=True)
        for i, q in enumerate(details["followups"]):
            if st.button(f"↩ {q}", key=f"fu-{key}-{i}"):
                st.session_state.pending = q
                st.rerun()


def render(user: dict) -> None:
    st.session_state.setdefault("conv_id", None)
    st.session_state.setdefault("pending", None)
    use_rewrite, use_bm25 = _sidebar(user)

    col_chat, col_plan = st.columns([2.3, 1], gap="large")
    with col_plan:
        student = tracker.render(user)

    with col_chat:
        messages = db.get_messages(st.session_state.conv_id) if st.session_state.conv_id else []
        last_assistant = max((i for i, m in enumerate(messages) if m["role"] == "assistant"), default=-1)
        for i, m in enumerate(messages):
            with st.chat_message(m["role"], avatar=domain.AVATAR if m["role"] == "assistant" else "🎓"):
                if m.get("details"):
                    st.markdown(render_answer(m["content"], m["details"].get("sources") or []),
                                unsafe_allow_html=True)
                    _details(m["details"], last=i == last_assistant and not st.session_state.pending, key=str(i))
                    if domain.DISCLAIMER and not m["details"].get("debug", {}).get("refused_by_gate"):
                        st.caption(domain.DISCLAIMER)
                else:
                    st.markdown(m["content"])

        if not messages and not st.session_state.pending:
            st.markdown(f"#### أهلاً {user['username']} 👋")
            st.caption(domain.APP_SUBTITLE)
            cols = st.columns(2)
            for i, q in enumerate(domain.EXAMPLE_QUESTIONS):
                if cols[i % 2].button(q, key=f"ex-{i}", use_container_width=True):
                    st.session_state.pending = q
                    st.rerun()

        busy = st.session_state.pending is not None
        answer_area = st.container()   # the new answer goes here, ABOVE the input box
        if question := st.chat_input("اكتب سؤالك هنا... (بالعامية أو الفصحى)" if not busy else "جاري كتابة الإجابة...",
                                     disabled=busy, key="chat_box"):
            st.session_state.pending = question
            st.rerun()

        if busy:
            with answer_area:
                _answer(user, messages, student, use_rewrite, use_bm25)


def _answer(user, messages, student, use_rewrite, use_bm25) -> None:
    question = st.session_state.pending
    with st.chat_message("user", avatar="🎓"):
        st.markdown(question)
    with st.chat_message("assistant", avatar=domain.AVATAR):
        try:
            pipeline = load_pipeline()
            with st.spinner("أبحث في وثائق بيرزيت..."):
                state = pipeline.prepare(question, [{"role": m["role"], "content": m["content"]} for m in messages],
                                         use_rewrite=use_rewrite, use_bm25=use_bm25, student=student)
            answer_text = st.write_stream(pipeline.stream(state))
            result = pipeline.finish(state, answer_text)
            if not result["refused"]:
                with st.spinner("أقترح أسئلة ذات صلة..."):
                    try:
                        result["followups"], usage = suggest_followups(question, result["answer"], result["sources"])
                        result["debug"]["tokens"]["input"] += usage["input_tokens"]
                        result["debug"]["tokens"]["output"] += usage["output_tokens"]
                    except Exception:   # follow-ups are a nice-to-have; never lose the answer for them
                        result["followups"] = []
        except Exception as e:   # missing key, network... show it, don't crash
            st.session_state.pending = None
            st.error(f"حدث خطأ: {e}")
            st.stop()
    if st.session_state.conv_id is None:
        st.session_state.conv_id = db.create_conversation(user["username"], question)
    db.add_user_message(st.session_state.conv_id, question)
    db.add_assistant_message(st.session_state.conv_id, result)
    st.session_state.pending = None
    st.rerun()
