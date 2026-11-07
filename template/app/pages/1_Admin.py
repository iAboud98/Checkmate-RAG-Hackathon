"""Admin page: upload/delete documents, edit their metadata, preview sections, rebuild the index."""

import re
from datetime import date

import streamlit as st
from common import load_pipeline, require_login, setup_page

from config import DOCS_DIR, SUPPORTED_EXTENSIONS
from src.ingest.build_index import build_index
from src.ingest.inspect import inspect_document
from src.ingest.loaders import list_documents, load_metadata, save_metadata

setup_page("الإدارة")
require_login(role="admin")
st.title("🛠️ إدارة المستندات")
st.caption(f"المجلد: `{DOCS_DIR}`")

DOCS_DIR.mkdir(parents=True, exist_ok=True)
metadata = load_metadata(DOCS_DIR)

# --- Upload ----------------------------------------------------------------------
uploads = st.file_uploader("رفع مستندات (PDF, DOCX, MD, TXT)", type=[e[1:] for e in SUPPORTED_EXTENSIONS],
                           accept_multiple_files=True)
if uploads and st.button("حفظ المستندات المرفوعة"):
    for f in uploads:
        (DOCS_DIR / f.name).write_bytes(f.getvalue())
        year = re.search(r"(19|20)\d{2}", f.name)
        metadata.setdefault(f.name, {"title": f.name.rsplit(".", 1)[0], "version": year.group(0) if year else "",
                                     "date": str(date.today()), "ocr": False})
    save_metadata(DOCS_DIR, metadata)
    st.success(f"تم حفظ {len(uploads)} ملف. عدّل البيانات أدناه ثم أعد بناء الفهرس.")
    st.rerun()

# --- Metadata table --------------------------------------------------------------
docs = list_documents(DOCS_DIR)
st.subheader(f"المستندات ({len(docs)})")
st.caption("الإصدار والتاريخ يحددان أي وثيقة هي الأحدث عند التعارض. فعّل OCR للملفات الممسوحة أو التالفة.")
rows = [{"file": p.name, "title": metadata.get(p.name, {}).get("title", p.stem),
         "version": metadata.get(p.name, {}).get("version", ""), "date": metadata.get(p.name, {}).get("date", ""),
         "ocr": bool(metadata.get(p.name, {}).get("ocr", False))} for p in docs]
edited = st.data_editor(rows, hide_index=True, disabled=["file"], use_container_width=True, key="meta")
if st.button("💾 حفظ البيانات"):
    for row in edited:
        metadata[row["file"]] = {**metadata.get(row["file"], {}), **{k: row[k] for k in ("title", "version", "date", "ocr")}}
    save_metadata(DOCS_DIR, metadata)
    st.success("تم الحفظ.")

c1, c2 = st.columns(2)
with c1:
    if st.button("🔄 إعادة بناء الفهرس", type="primary", use_container_width=True):
        with st.spinner("جاري القراءة والتقسيم والتضمين..."):
            try:
                n = build_index(verbose=False)
                load_pipeline.clear()
                st.success(f"تم. عدد المقاطع: {n}")
            except Exception as e:
                st.error(f"فشل البناء: {e}")
with c2:
    to_delete = st.selectbox("حذف مستند", ["—"] + [p.name for p in docs])
    if to_delete != "—" and st.button(f"🗑️ حذف {to_delete}", use_container_width=True):
        (DOCS_DIR / to_delete).unlink(missing_ok=True)
        metadata.pop(to_delete, None)
        save_metadata(DOCS_DIR, metadata)
        st.warning("تم الحذف. أعد بناء الفهرس.")
        st.rerun()

# --- Section preview -------------------------------------------------------------
st.subheader("معاينة الأقسام")
st.caption("هكذا سيُقسَّم المستند: مقطع واحد لكل قسم.")
choice = st.selectbox("المستند", [p.name for p in docs]) if docs else None
if choice:
    report = inspect_document(DOCS_DIR / choice, metadata.get(choice, {}))
    st.markdown(f"{report['sections']} أقسام → {len(report['chunks'])} مقاطع · {report['chars']} حرف")
    for w in report["warnings"]:
        st.warning(w)
    for c in report["chunks"]:
        indent = "　" * c["section_path"].count(" > ")
        with st.expander(f"{indent}{c['section_title']} · {len(c['text'])} حرف"):
            st.caption(c["section_path"])
            st.text(c["text"])
