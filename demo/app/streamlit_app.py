"""
MILESTONE 9: The user interface, a chat in Arabic (right-to-left).

Streamlit turns a Python script into a web page. The script reruns from the
top on every interaction; st.session_state keeps the chat between reruns, and
st.cache_resource keeps the loaded index in memory so we don't reload it.

Run from the demo/ folder:
    streamlit run app/streamlit_app.py
"""

import json
import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so "config" and "src" import

from config import RAW_DIR  # noqa: E402
from src.generation.answer import RagPipeline  # noqa: E402
from src.ingest.build_index import build_index  # noqa: E402

st.set_page_config(page_title="مساعد جامعة النخيل", page_icon="🎓", layout="centered")

# Right-to-left layout for Arabic. Code and scores stay left-to-right.
st.markdown("""
<style>
.stApp, .stChatMessage, .stMarkdown, .stExpander, section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
code, pre, .ltr { direction: ltr; text-align: left; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="جاري تحميل الفهرس...")
def load_pipeline() -> RagPipeline:
    return RagPipeline()


# --- Sidebar: settings to experiment with + upload new documents ------------
with st.sidebar:
    st.header("⚙️ إعدادات للتجربة")
    use_rewrite = st.toggle("إعادة صياغة السؤال (لهجة + سياق المحادثة)", value=True)
    use_bm25 = st.toggle("البحث الهجين (معاني + كلمات مفتاحية)", value=True)
    st.caption("أطفئ أحد الخيارين وقارن النتائج في لوحة «كيف وصلت للإجابة».")

    st.divider()
    st.header("📄 إضافة مستند")
    uploaded = st.file_uploader("ارفع ملف PDF", type="pdf")
    if uploaded and st.button("أضف وأعد بناء الفهرس"):
        (RAW_DIR / uploaded.name).write_bytes(uploaded.getvalue())
        meta_path = RAW_DIR / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        meta.setdefault(uploaded.name, {"title": Path(uploaded.name).stem, "version": "", "date": str(date.today())})
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        with st.spinner("جاري بناء الفهرس..."):
            n = build_index(verbose=False)
        load_pipeline.clear()  # forget the old index so the new one is loaded
        st.success(f"تمت الإضافة. عدد المقاطع في الفهرس: {n}")

    st.divider()
    if st.button("🗑️ محادثة جديدة"):
        st.session_state.messages = []
        st.rerun()

    st.caption("بيانات تجريبية خيالية. جامعة النخيل غير حقيقية.")


# --- Chat -------------------------------------------------------------------
st.title("🎓 مساعد جامعة النخيل")
st.caption("اسأل عن الأنظمة، الخطة الدراسية، التسجيل والرسوم. الإجابات من وثائق الجامعة فقط، مع ذكر المصدر.")

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "user"/"assistant", "content": str, "result": dict}]


def show_result_details(result: dict) -> None:
    """The two expanders under every answer: sources, and a look inside the pipeline."""
    if result["sources"]:
        with st.expander(f"📚 المصادر ({len(result['sources'])})"):
            for c in result["sources"]:
                st.markdown(f"**{c['source']}، ص {c['page']}** · {c['title']} - إصدار {c['version']}")
                st.text(c["text"])

    d = result["debug"]
    with st.expander("🔍 كيف وصلت للإجابة؟"):
        st.markdown(f"**السؤال الأصلي:** {d['question']}")
        st.markdown(f"**جملة البحث بعد إعادة الصياغة:** {d['search_query']}")
        gate = "❌ رفض قبل استدعاء النموذج" if d["refused_by_gate"] else "✅ تجاوز العتبة"
        st.markdown(f"**أعلى تشابه:** `{d['best_cosine']}` (العتبة `{d['threshold']}`) → {gate}")
        st.markdown("**المقاطع المسترجعة:**")
        st.dataframe(
            [{"الملف": c["source"], "ص": c["page"], **c["scores"]} for c in d["retrieved"]],
            hide_index=True,
        )
        st.caption(f"⏱️ {d['seconds']} ثانية · tokens: {d['tokens']['input']} in / {d['tokens']['output']} out")


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("result"):
            show_result_details(msg["result"])

if question := st.chat_input("اكتب سؤالك هنا... مثال: قديش بقدر أغيب؟"):
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("أبحث في الوثائق..."):
                result = load_pipeline().answer(question, history, use_rewrite=use_rewrite, use_bm25=use_bm25)
        except Exception as e:  # missing key, missing index, network... show it instead of crashing
            st.error(f"حدث خطأ: {e}")
            st.stop()
        st.markdown(result["answer"])
        show_result_details(result)

    st.session_state.messages.append({"role": "assistant", "content": result["answer"], "result": result})
