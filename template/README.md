# ♞ Checkmate · المرشد الذكي: an Arabic academic advisor for Birzeit University

> **Team Checkmate:** Aboud Fialah · Fadi Bassous · Adnan Odeh. IEEE RAG Hackathon, Bethlehem University, Nov 7 2026. Problem #1: Smart academic advisor.
> Birzeit students ask in Arabic (formal or Palestinian dialect) and get answers grounded in Birzeit's official regulations, the undergraduate guide and the engineering study plans, with the document, section and **page** cited, a clear refusal when the documents don't cover it, and a **personal course tracker** that knows which courses they still need.

---

## Install and run

Requires Python 3.12. Tesseract with Arabic is needed for the one scanned PDF (`brew install tesseract tesseract-lang`).

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
```
(or `python -m venv .venv && .venv/bin/pip install -r requirements.txt`)

```bash
cp .env.example .env
```
Then set `OPENAI_API_KEY` and `AUTH_USERS` in `.env` (make a login with `.venv/bin/python scripts/hash_password.py`; the password is stored only as a salted hash). `AUTH_ENABLED=false` skips logins for a quick local look.

Build everything from the organizers' zip (about 5 minutes, embedding cost well under $1):

```bash
.venv/bin/python scripts/import_dataset.py path/to/documents_dataset.zip
```
```bash
.venv/bin/python scripts/parse_study_plan.py
```
```bash
.venv/bin/python -m src.ingest.build_index
```
```bash
.venv/bin/python scripts/build_source_guide.py && .venv/bin/python scripts/build_faq.py
```
```bash
.venv/bin/streamlit run app/Home.py
```

`data/plans/computer_engineering.json`, `data/faq.json` and `data/source_guide.json` are committed, so steps 2 and 4 can be skipped.

---

## What the app does

| | |
|---|---|
| **Starter page** | Dark-green Checkmate hero (the deck's colours), live counts of indexed documents/sections, then login. |
| **♞ المرشد (chat)** | Streaming answers with **Perplexity-style numbered citation chips** `[1]`: hover shows document · section · page · snippet, click opens the official Ritaj page. Numbered source cards with the full text, a "how I got this answer" panel (rewritten query, similarity vs threshold, per-source scores), **3 follow-up questions** under each answer, saved history. |
| **🎓 Course tracker** | Next to the chat. The student ticks passed courses from the Computer Engineering 2026 plan, sees hours per requirement type (university / free / required / electives) and **what they can register now** (prerequisites met). Personal questions ("شو ضايلي؟", "بقدر آخذ ENCS3350؟") get the student's profile as a cited source. |
| **❓ FAQ** | Common questions answered ahead of time by the same RAG pipeline (with citations), searchable, plus a live "most asked" list. |
| **📚 Sources** | Every indexed document: category, version, pages, sections, Ritaj link, an automatic overview and key topics (labelled as automatic). |
| **Admin / Analytics** | Upload/delete documents, edit version/date/OCR, preview sections, rebuild; questions per day, refusal rate, latency, tokens, most-asked and unanswered questions (= content gaps). |

## The data (and the problems we solved in it)

From the organizers' zip (1,005 files) we import **student-facing** documents only:
- **36 regulations** (bachelor regulations 2025 and older versions, academic integrity, AI policy, fees, housing, scholarships, exchange, conduct...). Staff, HR, finance, museum and graduate-only documents are left out on purpose, so questions about them are refused.
- The **625-page undergraduate guide 2024-2025**, the **4 engineering study plans (April 2026)**, and a **scanned ministry decision (OCR)**.

| Problem in the data | Fix |
|---|---|
| The regulation PDFs store every Arabic word **reversed** (unreadable text layer) | Use the clean text twin from `documents.jsonl`, and recover each paragraph's **PDF page** by matching its words against the PDF's words (read forwards and backwards), with a monotonic dynamic-programming alignment so pages never jump backwards. Citations keep `ص N`. |
| The guide's text layer swaps lam-alef (`األكاديمي`) | Safe regex repairs for display (`األ→الأ`, lone `ال→لا`); BM25 normalization maps `لا`/`ال` to one form so broken and clean text still match. |
| Articles past the tenth (`المادة الحادية عشرة: التحذير الأكاديمي`) weren't detected, so they merged into article 10 | Heading pattern extended to all ordinals (colon required). Bachelor regulations went from 11 to 17 sections. |
| PyMuPDF's optional ONNX layout model segfaulted on the EE plan | `find_tables(use_layout=False)`: line-based table detection is enough for ruled tables. |
| One scanned PDF (no text layer) | Detected automatically, OCR with Tesseract `ara+eng`. |
| Study plan as structured data | `scripts/parse_study_plan.py` reads the plan table (pp. 5-7) and the English "Prerequisite:" lines: 50 courses, **138 hours, every requirement total matches the plan's page 1**. 6 courses are flagged `needs_review` (their prerequisite line couldn't be read) instead of guessed. |

## Architecture

```
 INDEXING (once / on admin "rebuild")                      ANSWERING (per question)

 dataset zip → import_dataset.py                           question + chat history (+ student's ticked courses)
   regulations: clean text + [[page N]] markers                │ rewrite (dialect → formal, follow-up → standalone)
   guide / plans: PDF (RTL line rebuild, tables)               ▼
   scanned: OCR                                            hybrid retrieval: vectors + BM25 → RRF → top-4 sections
        ▼                                                      │ + exact course-code lookup in the 2026 plan
 SECTIONS (one chunk per article/heading,                      │ + student profile (personal questions)
 breadcrumb, pages, version, Ritaj URL)                        ▼
        ▼                                                  refusal gate: best similarity < 0.40 → refuse (no LLM call)
 embeddings (title+version+path+text)                          ▼
        ▼                                                  grounded answer, streamed, citing [n] → chips + source cards
 data/index/ (NumPy + JSONL)                                   ▼
                                                           follow-up questions · SQLite history + analytics
 study plan PDF → parse_study_plan.py → plans/*.json  ──►  course tracker (progress, eligible-now)
```

| Layer | Files |
|---|---|
| Ingestion | `scripts/import_dataset.py`, `src/ingest/` (`pdf_loader`, `text_loader`, `ocr`, `cleanup`, `normalize`, `sections`, `build_index`) |
| Retrieval | `src/retrieval/` (`embedder`, `store`, `bm25`, `hybrid`) |
| Generation | `src/generation/` (`rewrite`, `prompts`, `llm`, `answer`, `followups`) + `domain.py` |
| Advisor | `scripts/parse_study_plan.py`, `src/advisor/plan.py`, `data/plans/computer_engineering.json` |
| App | `app/Home.py`, `app/common.py` (theme, starter page, login, citation chips), `app/views/` (`chat`, `tracker`, `faq`, `sources`), `app/pages/` (Admin, Analytics), `src/auth.py`, `src/storage/db.py` |
| Evaluation | `eval/questions.jsonl` (16 questions), `eval/run_eval.py`, `eval/results/` |

## Key design decisions

**Section-based chunking.** One chunk = one article/heading as the author structured it, so retrieval returns a whole rule and the section title is cited. Long sections are split at their numbered clauses and keep their title.

**Hybrid retrieval.** Embeddings (`text-embedding-3-large`) handle meaning and dialect paraphrases; BM25 over normalized Arabic handles exact tokens (course codes, numbers). Merged with Reciprocal Rank Fusion. Measured: dense-only loses the "how many times can I repeat a course" question that BM25 finds.

**Exact course lookup.** Embeddings are weak on codes like `ENCS3350`, and the 2024-25 guide has outdated course descriptions. A course code in the question pulls that course's row (credits, term, prerequisites, page) from the 2026 plan as its own cited source. This fixed the prerequisite and multi-turn eval questions.

**Personal context as a source, not a prompt hack.** The tracker writes the student's record (passed courses, hours per category, eligible courses, missing prerequisites) as one more numbered source. The LLM still answers only from sources, so personal answers are grounded and cited like everything else.

**Query rewriting.** A small model turns dialect into formal Arabic and makes follow-ups standalone, using few-shot examples from `domain.py`. It is never told the domain, so off-topic questions stay off-topic and get refused.

**Two-layer refusal.** (1) Best cosine below 0.40 → refuse without calling the LLM. Calibration: in-scope questions ≥ 0.53, off-topic ≤ 0.20. (2) The prompt's fixed refusal sentence catches questions that sound on-topic but aren't covered (e.g. the president's salary scores 0.59, and is still refused).

**Conflicting versions.** Each source carries its version/date. The model uses the newest and says what the older one said. Example: CE needs 138 hours in the 2026 plan; the 2024-25 guide said 158, and the answer cites both.

**Numbered citations.** The model cites `[n]`. That's shorter and more reliable than copying long labels. The app turns `[n]` into chips, and the eval expands `[n]` back to `[document، section، ص N]` for the judge.

## Evaluation

16 questions written before tuning (`eval/questions.jsonl`): 7 lookups, 2 dialect, 2 table/course-code, 1 version conflict, 1 multi-turn, 1 OCR document, 3 out-of-scope (one sounds on-topic). LLM judge = `gpt-5.4-mini`.

| Setup | Hit@4 | Precision@4 | Refusal acc. | Correct | Faithful | Cited | Avg time | Tokens/answer |
|---|---|---|---|---|---|---|---|---|
| First run (all student + graduate docs) | 0.77 | 0.33 | 0.88 | 0.77 | 0.85 | 0.85 | 3.4 s | 2,712 |
| **Final: hybrid + rewrite + course lookup** | **0.92** | **0.40** | **1.00** | **1.00** | **1.00** | **1.00** | 3.0 s | 2,882 |
| Final, dense only (no BM25) | 0.92 | 0.38 | 1.00 | 1.00 | 1.00 | 1.00 | 2.9 s | 2,735 |
| Final, no query rewriting | 0.92 | 0.35 | 0.94 | 0.92 | 0.85 | 0.92 | 1.5 s | 2,149 |

**What changed between the first and final run** (failure analysis):
- *q05 / q09 (probation GPA):* master's and PhD regulations (probation at 2.33 / 2.67) outranked the bachelor rule (2.00), and the dialect word "إنذار" differs from the documents' "التحذير". Fix: Checkmate serves undergraduates, so graduate-only documents were removed, plus a prompt rule to assume bachelor level.
- *q08 / q10 (ENCS3350 prerequisite, "and how many credits?"):* retrieval returned the 2024-25 guide's outdated description, or nothing. Fix: the exact course-code lookup in the 2026 plan.
- *Remaining retrieval miss (q03, withdrawal):* the answer is correct, but the top 4 were four OLDER copies of the same article ("المادة السابعة: الانسحاب" in the 2009, pre-2009 and undated regulations and the 2024-25 guide), so the 2025 version (the gold source) was crowded out. Next step: collapse sections with the same title across versions and keep the newest (version-aware de-duplication).
- *Ablations:* without BM25, the exact-wording question q04 ("كم مرة يجوز التسجيل في نفس المساق") misses its article. Without rewriting, the multi-turn follow-up "وكم ساعة معتمدة إله؟" is refused, and faithfulness drops to 0.85.

Precision@4 is low by construction: only 1-2 of the 4 sections come from the gold article, and the rest are neighbours (see LESSONS D4). Hit@4 is the main retrieval metric.

## Security and privacy
- API keys only in `.env` (git-ignored); `.env.example` documents every variable.
- Passwords: salted PBKDF2-SHA256 hashes, constant-time comparison; admin pages are role-protected.
- Documents, index, chat history and course ticks stay on the server (local files + SQLite). Only the question, the retrieved sections and (for personal questions) the student's course list are sent to OpenAI.
- Scaling: NumPy store → pgvector/FAISS, SQLite → Postgres, one index per university; cost ≈ tokens per answer (~2,800) × model price.

## Configuration
All knobs are in `config.py` / `.env`: models, `MAX_SECTION_CHARS`, `TOP_K`, `REFUSAL_THRESHOLD` (0.40), `OCR_ENGINE`, prices, auth. Everything problem-specific is in `domain.py`: identity, refusal sentence, FAQ list, plan keywords, which dataset documents to import, rewrite examples.

## AI disclosure and attribution
- We used **Claude Code (Claude Opus 5.5)** as a coding assistant. The base template was prepared with it the night before from our own design. During the hackathon it helped build the dataset import and page alignment, the study-plan parser, the course tracker, numbered citations, follow-ups, FAQ/source-guide generation, the Checkmate UI and the eval set. Every output was reviewed by the team. Detailed log: `AI_USAGE.md`.
- Data: Birzeit University regulations, undergraduate guide and study plans, provided by the organizers (scraped from Ritaj); each regulation links to its official Ritaj page.
- Libraries: OpenAI Python SDK, PyMuPDF, python-docx, rank-bm25, NumPy, Streamlit, python-dotenv, pytesseract/Tesseract OCR, Pillow. Font: Tajawal (Google Fonts, SIL Open Font License).
- UI ideas inspired by well-known RAG products (Perplexity's numbered citations and related questions, NotebookLM's source overviews); no code was copied from them or from any other project.
