# AI usage log

Required by the hackathon: the README must disclose AI tools and what they produced. Add a line whenever AI produces something.

| When | Tool | What it produced | Reviewed by |
|---|---|---|---|
| Nov 6 (night before) | Claude Code (Claude Opus 5.5) | This template: section-based ingestion (PDF/DOCX/MD/TXT, OCR), hybrid retrieval, grounded generation, Streamlit app (chat, history, admin, analytics, login), eval scripts, example documents, README | |
| Nov 7 | Claude Code (Claude Opus 5.5) | Student survey questions (Arabic) + Apps Script that builds the Google Form (`docs/survey/create_survey_form.gs`); first-pass market/cost research links | Aboud |
| Nov 7 | Claude Code (Claude Opus 5.5) | Business plan draft from team decisions (`docs/BUSINESS_PLAN.md`) and the 12-slide pitch deck (`deck/Checkmate_Pitch.pptx`, built with pptxgenjs) incl. speaker notes | Aboud |
| Nov 7 | Claude Code (Claude Opus 5.5) | One-file walkthrough of the whole template (stack, pipeline, data formats, eval, judge Q&A) in `docs/TEMPLATE_SUMMARY.md`, written from the code | Aboud |
| Nov 7 (build) | Claude Code (Claude Opus 5.5) | Dataset import (`scripts/import_dataset.py`) with page recovery for the reversed-text regulation PDFs; lam-alef repair; heading pattern for articles past the tenth; `find_tables(use_layout=False)` crash fix | Aboud |
| Nov 7 (build) | Claude Code (Claude Opus 5.5) | CE study-plan parser (`scripts/parse_study_plan.py` → `data/plans/computer_engineering.json`), course tracker logic (`src/advisor/plan.py`), student profile + exact course lookup as cited sources in `src/generation/answer.py` | Aboud (6 courses flagged for manual check) |
| Nov 7 (build) | Claude Code (Claude Opus 5.5) | Checkmate UI: theme from the deck, starter page, 3 tabs (`app/views/`), numbered citation chips, follow-up questions (`src/generation/followups.py`), FAQ and source-guide generators | Aboud |
| Nov 7 (build) | Claude Code (Claude Opus 5.5) | 16 Birzeit eval questions (gold answers copied from the regulations' text), eval runs and failure analysis, README rewrite | Aboud |
| Nov 7 (runtime) | gpt-5-nano | Source overviews (`data/source_guide.json`, labelled "ملخص آلي") and follow-up questions; FAQ answers come from the RAG pipeline itself | |
| | | | |
