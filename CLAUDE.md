# CLAUDE.md — Team Checkmate · IEEE RAG Hackathon

Team **Checkmate** (Aboud Fialah, Fadi Bassous, Adnan Odeh) is building an Arabic-first **RAG system + product pitch** in a **4.5-hour build (10:30 AM–3:00 PM, submit before 3:00)**. Goal: **win**. Every task is judged by the points it earns.

- Full rubric, the 10 problems, slide requirements, judge questions, timeline: **`docs/HACKATHON_GUIDE.md`**. Read the relevant section before working on scoring, the deck, business content, or problem choice.
- Problems already hit and their fixes (Arabic PDF extraction, OpenAI params, refusal, Streamlit...): **`docs/LESSONS_LEARNED.md`**. Read it before building ingestion, retrieval, or the UI.

## Current state
- **Problem:** **#1 Smart academic advisor (المرشد الذكي)**, assigned by organizers, **specific to Birzeit University** (its regulations, student guide, study plans). Users: university students & academic advisors. Data: student guide, university regulations, study plans (PDF). RAG challenge: exact answers with course codes, tables & prerequisites. Bonus idea: web app / WhatsApp bot + dashboard of most-repeated questions.
- **Roles:** Fadi + Adnan: UI and data. Aboud: business plan (`docs/BUSINESS_PLAN.md`) + deck (Google Slides).
- **Stack / starting point:** **`template/`** (read its README first). OpenAI (`gpt-5.4-mini` answers, `gpt-5-nano` rewrite, `text-embedding-3-large`), **section-based chunking** (one chunk per document section; PDF/DOCX/MD/TXT + OCR), NumPy + BM25 hybrid with RRF, two-layer refusal, Streamlit app with login, saved history, admin and analytics. The problem goes into `domain.py` + `data/raw/`. `demo/` is learning material only, so don't build on it.

## Rules for Claude (non-negotiable)
1. **Never fabricate numbers, stats, or sources.** Business content either cites a real, checkable source or is labeled **assumption**. Fabrication costs 3–5 points.
2. **Never commit secrets.** Keys come from env vars. Keep `.env` git-ignored and `.env.example` in sync. An exposed key costs 2 points.
3. **Attribute all external code** in the README. Copying without attribution costs up to 10 points or gets the team disqualified.
4. **Grounded answers only.** The system answers from retrieved context, cites `[doc, p.N]`, and **refuses** when the sources don't cover the question. Never let it hallucinate.
5. **Working end-to-end first, then measure, then improve.** Never break the working demo, especially after feature freeze (~1:15 PM).
6. **Explain what you build.** After any non-trivial code, add 2–3 lines on how to explain it to a judge ("explain this part of the code" is a standard judge question).
7. **Log AI usage** in `AI_USAGE.md` as you go (tool and what it produced). It feeds the required README disclosure.
8. **Say which rubric item a task serves.** Cut work that scores nothing.
9. **Log every problem you hit, with its fix,** in `docs/LESSONS_LEARNED.md` as soon as it's solved (symptom → cause → fix → what to do next time).
10. Talk to the team in English. Arabic is fine for prompts, UI text and sample answers.

## Scoring at a glance (100 + 10 bonus)
| Criterion | Pts | Where the points are |
|---|---|---|
| RAG technical quality | **30** | Data prep 5 · Retrieval 10 · Grounding & citations 10 · Evaluation 5 |
| Problem understanding | 15 | Size + evidence · Why RAG · Arabic/local fit |
| Code & engineering | 15 | Clean layers · Runs from README alone · Security & scaling |
| Business plan | 15 | TAM/SAM/SOM (sourced) · Pricing & unit economics · Costs, 12–36mo projections, break-even |
| Marketing | 10 | Persona · Channels & launch · KPIs + 90-day plan |
| Presentation | 10 | Story · Live demo with sources (no demo or video = 0) · Q&A |
| Innovation | 5 | e.g. dialect handling, multi-agent, auto-eval loop, voice/image |
| **Bonus** | +10 | Working product 5 · Arabic RTL UX 2 · Login/admin/upload/history/analytics 3. **Only counts with ≥15/30 on RAG.** |

Tie-breaks: RAG score, then **Evaluation** score.

## The system must handle (judges test live, including 1 out-of-scope question)
- In-scope question → correct answer **with citation (doc + page)**
- **Out-of-scope** question → clean refusal (retrieval-score threshold before calling the LLM, plus the prompt rule)
- **Dialect** question over MSA docs → rewrite to MSA before retrieval
- **Scanned PDFs / tables** → OCR fallback; keep tables intact with their headers
- **Conflicting versions** → prefer newest `version/date`, flag the conflict, cite both
- **Multi-turn** → condense history into a standalone query before retrieval

## Repo layout (keep layers separate; judges read the code)
```
domain.py        everything problem-specific (assistant identity, refusal sentence, disclaimer, UI text, rewrite examples)
config.py        all knobs, read from .env
src/ingest/      loaders (pdf/docx/text/ocr) → blocks → sections.py (one chunk per section) → build_index.py
src/retrieval/   embeddings, NumPy vector store, BM25, hybrid RRF
src/generation/  rewrite, prompts, llm (+streaming), answer pipeline (prepare → stream → finish)
src/storage/     SQLite history + analytics;  src/auth.py  hashed logins + roles
app/             Home.py (chat), pages/1_Admin.py, pages/2_Analytics.py; Arabic RTL
eval/            questions.jsonl (≥12 Qs, gold section/page), run_eval.py (--calibrate, --dense-only, --no-rewrite)
scripts/         check_extraction.py (run FIRST on new docs), list_models.py, hash_password.py
data/raw/        organizers' docs + metadata.json (version/date/ocr per file)
```

## Evaluation (5 pts + tie-break #2)
- `eval/questions.jsonl`: at least 12 questions written **before** tuning. Mix: lookups, tables, ≥2 dialect, ≥2 out-of-scope, 1 conflicting-version, 1 multi-turn.
- `python eval/run_eval.py` reports Precision@k, Faithfulness (LLM-as-judge), refusal accuracy, latency, and cost per answer.
- Keep a **before → after table** plus one failure analysis for the README and a slide.

## Submission checklist (before 3:00 PM; −2 points per 5 min late)
- [ ] Repo/zip: README (install, run, architecture, eval results, **AI disclosure**, attribution), pinned `requirements.txt`, `.env.example`, sample data
- [ ] Deck: PDF/PPTX, **≤12 slides**, covering the 9 required slides (guide §3)
- [ ] Deck placeholders filled (red XX / N): survey results (slides 2, 11), eval table (slide 5), demo screenshot + answer + video link (slide 4)
- [ ] 2–3 min demo video: one answer with a source, one out-of-scope refusal
- [ ] Fresh-clone test on another laptop + secret scan before the final push
