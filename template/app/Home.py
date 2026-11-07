"""
Checkmate: the main page.   Run from the template/ folder:   streamlit run app/Home.py

Starter page -> login -> three tabs:
    الأسئلة الشائعة (FAQ)  |  المرشد (the RAG chat + course tracker)  |  المصادر (every document, with an overview)
Each tab lives in app/views/ so the page stays short.
"""

import streamlit as st
from common import header, index_exists, require_login, setup_page
from views import chat, faq, sources

import domain

setup_page(domain.APP_TITLE)
user = require_login(show_landing=True)
header()

if not index_exists():
    st.warning("لا يوجد فهرس بعد. على المشرف رفع المستندات وبناء الفهرس من صفحة الإدارة.")
    st.stop()

TABS = ["❓ الأسئلة الشائعة", "♞ المرشد", "📚 المصادر"]
if st.session_state.pop("goto_chat", False):   # "ask this" buttons in other tabs jump to the chat
    st.session_state["main_tabs"] = TABS[1]
tab_faq, tab_chat, tab_sources = st.tabs(TABS, default=TABS[1], key="main_tabs")

with tab_faq:
    faq.render()
with tab_chat:
    chat.render(user)
with tab_sources:
    sources.render()
