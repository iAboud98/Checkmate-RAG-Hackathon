"""Shared by all pages: page setup + Checkmate theme (RTL), starter page, login, citation chips, cached pipeline."""

import html
import json
import re
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so "config", "domain", "src" import

import domain  # noqa: E402
from config import AUTH_ENABLED, AUTH_USERS, DOCS_DIR, INDEX_DIR  # noqa: E402
from src.auth import authenticate  # noqa: E402

# Colours = the deck's "Checkmate Olive" theme, so the app and the slides look like one product.
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
:root {
  --cm-dark: #1F4E3D; --cm-primary: #2E7D5B; --cm-bg: #EEF4F0; --cm-mint: #BFD6CA;
  --cm-ink: #1B2B24; --cm-gold: #E0A43A; --cm-sage: #6B8F7E; --cm-card: #FFFFFF;
}
html, body, .stApp, .stMarkdown, button, input, textarea, [data-testid="stChatInput"] textarea {
  font-family: 'Tajawal', 'Segoe UI', sans-serif !important;
}
.stApp, .stChatMessage, .stMarkdown, .stExpander, section[data-testid="stSidebar"], .stForm,
[data-testid="stTabs"], [data-testid="stDialog"] { direction: rtl; text-align: right; }
code, pre, .ltr, .stDataFrame { direction: ltr; text-align: left; }
.stApp { background: linear-gradient(180deg, #E3EFE8 0%, var(--cm-bg) 260px); }

/* Sidebar: dark green like the title slide */
section[data-testid="stSidebar"] { background: var(--cm-dark); }
section[data-testid="stSidebar"] * { color: #F3F8F5 !important; }
section[data-testid="stSidebar"] button { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.18); }
section[data-testid="stSidebar"] button:hover { border-color: var(--cm-gold); }

/* Header band */
.cm-header { display: flex; align-items: center; gap: 14px; background: var(--cm-dark); color: #fff;
  border-radius: 18px; padding: 14px 22px; margin-bottom: 10px; box-shadow: 0 6px 18px rgba(31,78,61,0.18); }
.cm-header .cm-logo { width: 46px; height: 46px; border-radius: 50%; background: var(--cm-gold);
  display: flex; align-items: center; justify-content: center; font-size: 28px; color: var(--cm-dark); }
.cm-header .cm-name { font-size: 1.45rem; font-weight: 800; letter-spacing: 0.5px; }
.cm-header .cm-sub { font-size: 0.92rem; opacity: 0.85; }

/* Tabs */
[data-testid="stTabs"] [role="tablist"] { gap: 6px; border-bottom: 2px solid var(--cm-mint); }
[data-testid="stTabs"] button[role="tab"] { font-size: 1.05rem; font-weight: 700; padding: 8px 18px;
  border-radius: 12px 12px 0 0; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background: var(--cm-primary); color: #fff; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p { color: #fff; }

/* Cards */
.cm-card { background: var(--cm-card); border: 1px solid var(--cm-mint); border-radius: 16px;
  padding: 16px 18px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(31,78,61,0.06); }
.cm-card h4 { margin: 0 0 6px 0; color: var(--cm-dark); font-size: 1.05rem; }
.cm-muted { color: var(--cm-sage); font-size: 0.86rem; }
.cm-badge { display: inline-block; background: var(--cm-bg); color: var(--cm-dark); border: 1px solid var(--cm-mint);
  border-radius: 999px; padding: 1px 10px; font-size: 0.78rem; margin: 2px 0 2px 4px; }
.cm-badge.gold { background: #FBF1DE; border-color: var(--cm-gold); color: #7A5410; }
.cm-badge.code { direction: ltr; font-family: ui-monospace, monospace; }

/* Citation chips: [n] in answers -> green bubble with a hover card (doc · section · page) */
.cm-cite { position: relative; display: inline-flex; align-items: center; justify-content: center;
  min-width: 1.35em; height: 1.35em; padding: 0 4px; margin: 0 2px; border-radius: 999px;
  background: var(--cm-primary); color: #fff !important; font-size: 0.72em; font-weight: 700;
  vertical-align: super; text-decoration: none !important; cursor: pointer; }
.cm-cite:hover { background: var(--cm-gold); color: var(--cm-dark) !important; }
.cm-cite .cm-tip { visibility: hidden; opacity: 0; position: absolute; bottom: 140%; right: -10px; z-index: 50;
  width: 280px; background: var(--cm-dark); color: #fff; text-align: right; font-weight: 400;
  font-size: 0.8rem; line-height: 1.45; padding: 10px 12px; border-radius: 10px;
  box-shadow: 0 8px 20px rgba(0,0,0,0.25); transition: opacity .15s; white-space: normal; }
.cm-cite:hover .cm-tip { visibility: visible; opacity: 1; }
.cm-tip b { color: var(--cm-gold); }
.cm-src { border-right: 4px solid var(--cm-primary); background: #F7FBF8; border-radius: 10px;
  padding: 8px 12px; margin: 6px 0; }
.cm-src .n { display: inline-block; background: var(--cm-primary); color: #fff; border-radius: 999px;
  min-width: 1.5em; text-align: center; font-weight: 700; margin-left: 6px; }
.cm-src.personal { border-right-color: var(--cm-gold); }

/* Starter page */
.cm-hero { background: radial-gradient(circle at 15% 20%, #2E7D5B 0%, #1F4E3D 55%, #173B2E 100%);
  color: #fff; border-radius: 28px; padding: 56px 40px 46px; text-align: center; margin-top: 10px;
  box-shadow: 0 18px 40px rgba(31,78,61,0.35); }
.cm-hero .logo { width: 92px; height: 92px; margin: 0 auto 14px; border-radius: 50%; background: var(--cm-gold);
  color: var(--cm-dark); font-size: 58px; display: flex; align-items: center; justify-content: center; }
.cm-hero h1 { color: #fff; font-size: 3rem; font-weight: 800; margin: 0; letter-spacing: 1px; }
.cm-hero .tag { color: var(--cm-gold); font-size: 1.35rem; font-weight: 700; margin-top: 4px; }
.cm-hero p { color: #DCEBE3; font-size: 1.05rem; max-width: 640px; margin: 14px auto 0; }
.cm-stats { display: flex; justify-content: center; gap: 28px; flex-wrap: wrap; margin-top: 26px; }
.cm-stats div { text-align: center; } .cm-stats b { display: block; font-size: 1.6rem; color: var(--cm-gold); }
.cm-stats span { font-size: 0.85rem; color: #CFE3D8; }
.cm-feature { background: #fff; border: 1px solid var(--cm-mint); border-radius: 18px; padding: 20px; height: 100%;
  text-align: right; box-shadow: 0 4px 12px rgba(31,78,61,0.07); }
.cm-feature .ic { font-size: 1.8rem; } .cm-feature h4 { color: var(--cm-dark); margin: 6px 0; }
.cm-feature p { color: #44564D; font-size: 0.93rem; margin: 0; }
div.stButton > button[kind="primary"] { background: var(--cm-primary); border: none; font-weight: 700; }
div.stButton > button[kind="primary"]:hover { background: var(--cm-dark); }
@media (max-width: 640px) { .cm-hero { padding: 36px 18px; } .cm-hero h1 { font-size: 2.2rem; } }
</style>
"""


def setup_page(title: str, layout: str = "wide") -> None:
    st.set_page_config(page_title=f"{title} · {domain.BRAND}", page_icon=domain.APP_ICON, layout=layout)
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def header(subtitle: str = "") -> None:
    st.markdown(f"""<div class="cm-header"><div class="cm-logo">{domain.APP_ICON}</div>
        <div><div class="cm-name">{domain.BRAND}</div>
        <div class="cm-sub">{html.escape(subtitle or domain.APP_TAGLINE)}</div></div></div>""",
                unsafe_allow_html=True)


# --- starter page + login --------------------------------------------------------

def corpus_stats() -> dict:
    """Counts shown on the starter page, read from the real metadata (not typed in)."""
    meta_path = DOCS_DIR / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    kinds = [m.get("kind", "") for m in meta.values()]
    chunks = INDEX_DIR / "chunks.jsonl"
    n_chunks = sum(1 for _ in chunks.open(encoding="utf-8")) if chunks.exists() else 0
    return {"regulations": kinds.count("regulation"), "plans": kinds.count("plan"), "chunks": n_chunks,
            "docs": len(meta)}


def landing() -> None:
    s = corpus_stats()
    st.markdown(f"""<div class="cm-hero"><div class="logo">{domain.APP_ICON}</div>
      <h1>{domain.BRAND}</h1><div class="tag">المرشد الذكي لطلبة جامعة بيرزيت</div>
      <p>{html.escape(domain.APP_SUBTITLE)}</p>
      <div class="cm-stats">
        <div><b>{s['docs']}</b><span>وثيقة رسمية</span></div>
        <div><b>{s['regulations']}</b><span>نظام وتعليمات</span></div>
        <div><b>{s['plans']}</b><span>خطط دراسية</span></div>
        <div><b>{s['chunks']:,}</b><span>قسم مفهرس</span></div>
      </div></div>""", unsafe_allow_html=True)
    st.write("")
    features = [
        ("📚", "من الوثائق الرسمية فقط", "كل إجابة مع اسم الوثيقة ورقم الصفحة، ورفض صريح إذا لم تكن المعلومة موجودة."),
        ("🗣️", "اسأل بلهجتك", "اكتب بالعامية الفلسطينية، والمرشد يحوّل سؤالك للفصحى قبل البحث."),
        ("🎓", "خطتك الدراسية", "علّم المساقات التي أنهيتها، واعرف ما تبقى وما تستطيع تسجيله الآن."),
    ]
    for col, (icon, title, text) in zip(st.columns(3), features):
        col.markdown(f"""<div class="cm-feature"><div class="ic">{icon}</div><h4>{title}</h4><p>{text}</p></div>""",
                     unsafe_allow_html=True)
    st.write("")
    _, mid, _ = st.columns([1, 1, 1])
    if mid.button("ابدأ الآن ←", type="primary", use_container_width=True):
        st.session_state.started = True
        st.rerun()
    st.caption("فريق Checkmate · هاكاثون IEEE للـ RAG · " + domain.DISCLAIMER)


def current_user() -> dict | None:
    if not AUTH_ENABLED:
        return {"username": "dev", "role": "admin"}
    return st.session_state.get("user")


def require_login(role: str | None = None, show_landing: bool = False) -> dict:
    """Starter page (Home only) -> login form -> page. With role="admin", block other roles."""
    if show_landing and not st.session_state.get("started"):
        landing()
        st.stop()
    user = current_user()
    if user is None:
        _, mid, _ = st.columns([1, 1.2, 1])
        with mid:
            header("تسجيل الدخول")
            if not AUTH_USERS:
                st.error("No users configured. Run `python scripts/hash_password.py` and add AUTH_USERS to .env "
                         "(or set AUTH_ENABLED=false while developing).")
                st.stop()
            with st.form("login"):
                username = st.text_input("اسم المستخدم")
                password = st.text_input("كلمة المرور", type="password")
                if st.form_submit_button("دخول", type="primary", use_container_width=True):
                    user = authenticate(username, password)
                    if user:
                        st.session_state.user = user
                        st.rerun()
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")
        st.stop()
    with st.sidebar:   # drawn before the role check, so a blocked user can still log out
        st.markdown(f"### {domain.APP_ICON} {domain.BRAND}")
        st.caption(f"👤 {user['username']} ({user['role']})")
        if AUTH_ENABLED and st.button("تسجيل الخروج"):
            st.session_state.clear()
            st.rerun()
    if role and user["role"] != role:
        st.error("هذه الصفحة متاحة للمشرفين فقط.")
        st.stop()
    return user


# --- citations ----------------------------------------------------------------------

CITE = re.compile(r"\[(\d+)\]")


def page_label(s: dict) -> str:
    if not s.get("page_start"):
        return ""
    return f"ص {s['page_start']}" if s["page_start"] == s.get("page_end") else f"ص {s['page_start']}-{s['page_end']}"


def render_answer(text: str, sources: list[dict]) -> str:
    """Perplexity-style: every [n] becomes a numbered chip; hover shows document, section, page and a
    snippet; click opens the official Ritaj page when the source has one."""
    by_n = {s.get("n", i): s for i, s in enumerate(sources, start=1)}

    def chip(m: re.Match) -> str:
        s = by_n.get(int(m.group(1)))
        if not s:
            return m.group(0)
        snippet = html.escape(" ".join(s.get("text", "").split())[:220]) + "…"
        tip = (f"<b>{html.escape(s.get('doc_title') or '')}</b><br>{html.escape(s.get('section_title') or '')}"
               f" · {page_label(s)}<br><span style='opacity:.8'>{snippet}</span>")
        href = f' href="{html.escape(s["url"])}" target="_blank"' if s.get("url") else ""
        return f'<a class="cm-cite"{href}>{m.group(1)}<span class="cm-tip">{tip}</span></a>'

    return CITE.sub(chip, text)


def show_sources(sources: list[dict], cited: list[int] | None = None) -> None:
    """Numbered source cards under an answer; the ones the answer cites come first."""
    if not sources:
        return
    cited = cited or []
    ordered = sorted(sources, key=lambda s: (s.get("n") not in cited, s.get("n") or 0))
    with st.expander(f"📚 المصادر ({len(sources)})", expanded=False):
        for s in ordered:
            personal = " personal" if s.get("kind") == "profile" else ""
            link = f' · <a href="{html.escape(s["url"])}" target="_blank">رتاج ↗</a>' if s.get("url") else ""
            used = "" if s.get("n") in cited else ' <span class="cm-muted">(لم يُستشهد به)</span>'
            st.markdown(f"""<div class="cm-src{personal}"><span class="n">{s.get('n', '')}</span>
                <b>{html.escape(s.get('doc_title') or '')}</b> · {html.escape(s.get('section_title') or '')}
                · {page_label(s)}{link}{used}<br><span class="cm-muted">{html.escape(s.get('section_path') or '')}</span>
                </div>""", unsafe_allow_html=True)
            with st.popover("النص الكامل", use_container_width=False):
                st.text(s.get("text", ""))


@st.cache_resource(show_spinner="جاري تحميل الفهرس...")
def load_pipeline():
    from src.generation.answer import RagPipeline
    return RagPipeline()


def index_exists() -> bool:
    return (INDEX_DIR / "embeddings.npy").exists()
