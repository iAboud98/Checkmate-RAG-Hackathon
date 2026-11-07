# Template: everything in one file

Team Checkmate · IEEE RAG Hackathon · Nov 7, 2026
A complete walkthrough of `template/`: every technology, every file, every design decision, the data formats, the eval results, and how to explain each part to a judge.

> Written from the actual code in `template/` (about 2,160 lines of Python). If code and this file disagree, the code wins.

---

## 0. Where things stand right now (read first)

The template is a **working, tested RAG system**, but it is still configured for the **fictional example company** ("شركة الأفق للبرمجيات"). It has **not been switched to Birzeit yet**:

| Item | Current value | Needs to become |
|---|---|---|
| `domain.py` | Al-Ofoq assistant (HR, travel, IT security) | Birzeit academic advisor (المرشد الذكي) |
| `.env` → `DOCS_DIR` | `data/examples` | `data/raw` |
| `data/raw/` | empty (only `.gitkeep`) | Birzeit student guide, regulations, study plans + `metadata.json` |
| `data/index/` | 18 chunks built from the 4 example files | rebuilt from the Birzeit docs |
| `eval/questions.jsonl` | 14 questions about the example docs | ≥12 Birzeit questions (written before tuning) |
| `README.md` | eval table and placeholders are for the example docs | real problem, real eval, real numbers |

The steps to switch are in section 13.

---

## 1. What the system does, in one paragraph

A student asks a question in Arabic (formal or dialect). A small model **rewrites** it into a clear, standalone formal-Arabic search query. **Hybrid retrieval** (meaning-based vectors + exact-keyword BM25, merged with Reciprocal Rank Fusion) finds the 4 most relevant **document sections**. If even the best match is weak, the system **refuses without calling the LLM**. Otherwise the LLM writes a **grounded answer, streamed**, citing `[file، section، page]` after every fact, using the newest version when documents conflict, and refusing with a fixed sentence if the sections don't contain the answer. Everything is saved to SQLite for **chat history and analytics**.

---

## 2. Technology stack (every library and service)

### Runtime
| Thing | Version / value | Used for |
|---|---|---|
| Python | 3.12 | everything |
| `uv` | (tool) | fast venv + install (`uv venv`, `uv pip install`) |

### Python libraries (`requirements.txt`, all pinned)
| Package | Version | What we use it for | Where |
|---|---|---|---|
| `openai` | 3.46.0 | embeddings, chat (answer, rewrite, judge), vision OCR, model listing | `src/openai_client.py`, `src/generation/llm.py`, `src/retrieval/embedder.py`, `src/ingest/ocr.py` |
| `pymupdf` | 2.1 | PDF reading: words with positions, font sizes, bold flags, table detection, outline/TOC, rendering pages to images for OCR | `src/ingest/pdf_loader.py`, `src/ingest/ocr.py` |
| `python-docx` | 1.2.0 | Word files: paragraphs, heading styles, tables, in body order | `src/ingest/docx_loader.py`, `scripts/make_examples.py` |
| `rank-bm25` | 0.2.2 | `BM25Okapi` keyword search | `src/retrieval/bm25.py` |
| `numpy` | 2.5.4 | vector store (matrix multiply = cosine search), saving `embeddings.npy` | `src/retrieval/store.py`, `embedder.py` |
| `streamlit` | 1.67.0 | the web app: chat, streaming, login form, admin, analytics charts | `app/` |
| `python-dotenv` | 1.2.4 | load `.env` into settings | `config.py` |
| `pytesseract` | 0.3.13 | offline OCR for scanned pages | `src/ingest/ocr.py` |
| `pillow` | 13.0.0 | turn the rendered page into an image for Tesseract | `src/ingest/ocr.py` |

### Standard library pieces worth naming
`sqlite3` (history + analytics DB), `hashlib.pbkdf2_hmac` + `hmac.compare_digest` (password hashing), `re` (Arabic heading patterns, cleanup), `json`/JSONL (index + metadata + eval), `dataclasses`, `uuid`, `argparse`, `getpass`.

### External tools / services
| Tool | Needed? | Used for |
|---|---|---|
| **OpenAI API** | yes | all models below |
| **Tesseract OCR** + Arabic data (`brew install tesseract tesseract-lang`) | only for scanned PDFs with `OCR_ENGINE=tesseract` | reading pages with no text layer |
| **Google Chrome** (headless) | only for `scripts/make_examples.py` | rendering the fictional Arabic example PDF with ligatures off |

### OpenAI models (all set in `.env`, never hard-coded)
| Role | Default | Setting | Why this one |
|---|---|---|---|
| Write the answer | `gpt-5.4-mini` | `OPENAI_CHAT_MODEL` | measured 3.7 s vs 5.2 s for `gpt-5-mini`, same correct answer (LESSONS B3) |
| Rewrite the query | `gpt-5-nano` | `OPENAI_REWRITE_MODEL` | small, cheap, fast; the task is simple |
| Embeddings | `text-embedding-3-large` (3072 dims) | `OPENAI_EMBEDDING_MODEL` | strong multilingual/Arabic meaning |
| Eval judge | = chat model | `OPENAI_JUDGE_MODEL` | grades correct / faithful |
| Vision OCR | = chat model | `OPENAI_VISION_MODEL` | reads scanned pages and keeps tables |
| Reasoning effort | `low` | `OPENAI_REASONING_EFFORT` | sent only to `gpt-5*` / `o*` models |

---

## 3. Folder map (every file)

```
template/
├── README.md              submission README (install, run, architecture, eval, security, AI disclosure)
├── AI_USAGE.md            log of AI tool usage (feeds the README disclosure)
├── requirements.txt       pinned dependencies
├── .env.example           every setting documented, no secrets
├── .env                   real key + users (git-ignored, never commit)
├── .gitignore             .env, .venv/, __pycache__/, data/index/, data/app.db, eval/results/, .DS_Store
├── config.py              ALL knobs, read from .env
├── domain.py              ALL problem-specific wording (the one file to edit for Birzeit)
│
├── src/
│   ├── openai_client.py   one shared OpenAI client (cached), clear error if key missing
│   ├── auth.py            PBKDF2 password hashing + login check + roles
│   ├── ingest/
│   │   ├── blocks.py        common Block format + table rows → "header: value"
│   │   ├── cleanup.py       RTL tidy-ups, Arabic heading regexes, header/footer detection, lam-alef detector
│   │   ├── normalize.py     Arabic normalization + tokenizer for BM25
│   │   ├── pdf_loader.py    PDF → blocks (RTL line rebuild, font-size headings, tables, OCR fallback)
│   │   ├── docx_loader.py   DOCX → blocks (heading styles, bold/regex fallback, tables)
│   │   ├── text_loader.py   Markdown and TXT → blocks
│   │   ├── ocr.py           scanned page → blocks (Tesseract or vision model)
│   │   ├── loaders.py       picks the loader by extension; reads/writes metadata.json
│   │   ├── sections.py      SECTION-BASED CHUNKING + citation label + embedding text
│   │   ├── inspect.py       preview a document's chunks + warnings (admin page + check script)
│   │   └── build_index.py   files → blocks → sections → chunks → embeddings → data/index/
│   ├── retrieval/
│   │   ├── embedder.py      OpenAI embeddings in batches of 100, normalized to length 1
│   │   ├── store.py         NumPy vector store (search = one matrix multiply), save/load
│   │   ├── bm25.py          BM25 over normalized Arabic tokens
│   │   └── hybrid.py        dense + BM25 → RRF → top-k, keeps per-chunk scores
│   ├── generation/
│   │   ├── prompts.py       answer prompt (grounding rules) + rewrite prompt (few-shot)
│   │   ├── rewrite.py       dialect → formal, follow-up → standalone
│   │   ├── llm.py           chat + streaming wrapper, token usage, safe params
│   │   └── answer.py        RagPipeline: prepare → stream → finish (+ CLI)
│   └── storage/
│       └── db.py            SQLite: conversations, messages, analytics queries
│
├── app/
│   ├── Home.py            chat page (streaming, citations, sources, "how I got this answer", history)
│   ├── common.py          RTL CSS, login gate, cached pipeline
│   └── pages/
│       ├── 1_Admin.py     upload/delete docs, edit version/date/OCR, preview sections, rebuild index
│       └── 2_Analytics.py usage, refusal rate, latency, tokens/cost, most-asked, unanswered
│
├── eval/
│   ├── questions.jsonl    the eval set (currently 14 example questions)
│   ├── run_eval.py        metrics, LLM judge, --calibrate / --dense-only / --no-rewrite
│   └── results/full.json  last saved run (git-ignored)
│
├── scripts/
│   ├── check_extraction.py  RUN FIRST on new docs: section tree + warnings
│   ├── hash_password.py     make an AUTH_USERS entry
│   ├── list_models.py       which models your key can use
│   └── make_examples.py     generates the 4 fictional example docs
│
└── data/
    ├── raw/               organizers' docs go here (+ metadata.json)
    ├── examples/          4 fictional docs + metadata.json (delete when real docs are in)
    ├── index/             chunks.jsonl + embeddings.npy (built, git-ignored)
    └── app.db             SQLite history (git-ignored)
```

**Judge line:** "Every layer is its own folder: ingest, retrieval, generation, storage, app. Settings are in `config.py`, problem wording in `domain.py`, so switching the problem touches one file and the docs folder."

---

## 4. The full pipeline, end to end

```
 INDEXING (once, or when admin clicks "rebuild")          ANSWERING (every question)

 PDF ─┐ text layer → RTL line rebuild, tables,            question + chat history
 DOCX ├ headers/footers removed; scanned → OCR                 │ 1. rewrite (gpt-5-nano)
 MD  ─┤                                                         ▼
 TXT ─┘        ▼                                           2. hybrid retrieval
          blocks (heading / text / table)                     vectors top-15 + BM25 top-15 → RRF → top-4
               ▼                                                ▼
          SECTIONS (one chunk per section,                 3. refusal gate: best cosine < 0.30 → refuse, no LLM
          breadcrumb, pages, version/date)                      ▼
               ▼                                           4. grounded answer (gpt-5.4-mini), streamed,
          embed: title + version + path + text                cites [file، section، ص N]
               ▼                                                ▼
          data/index/ (embeddings.npy + chunks.jsonl)      5. SQLite: history + analytics
```

---

## 5. Ingestion in detail (`src/ingest/`) — Data prep, 5 pts

### 5.1 The common format: Blocks (`blocks.py`)
Every loader, whatever the file type, outputs an ordered list of `Block(type, text, level, page)`:
- `type`: `heading` | `text` | `table`
- `level`: heading depth (1 = top)
- `page`: PDF page number; `None` for DOCX/MD/TXT (they have no pages)

**Tables** become one line per row, `header: value | header: value`, so a value never loses the column it belongs to (e.g. `البدل: بدل مواصلات | القيمة الشهرية: 150 شيكل | الشرط: لجميع الموظفين`). This is how "tables & prerequisites" stay answerable.

**Judge line:** "Four file types become one format, so the chunker only understands one thing."

### 5.2 PDF loader (`pdf_loader.py`) — the hardest part
Per page:
1. **Scanned?** If the page has fewer than 20 characters of text (`MIN_TEXT_CHARS`), or `metadata.json` says `"ocr": true`, the page goes to OCR (5.5).
2. **Tables first.** `page.find_tables()` gives table boxes. Lines inside a table box are removed from normal text (otherwise bold header cells would become section headings, LESSONS A10). For each cell, the words inside its box are collected and sorted, and each row is **reversed** (PDF cells come left-to-right, Arabic reads right-to-left). Rows → `header: value`.
3. **RTL line rebuild (LESSONS A2).** For every text line, take the words that sit inside the line's box (`page.get_text("words")`) and sort them by x **descending** (right to left). This fixes numbers and punctuation landing in the wrong place.
4. **`tidy()` cleanup (cleanup.py):** removes invisible bidi marks; `"%15"→"15%"`; removes space before `. , : ، ؛`; fixes mirrored parentheses `"1( )"→"(1)"`, `")1("→"(1)"`; strips punctuation pushed to the line start; `"الثاني.2025"→"الثاني 2025."`.
5. For each line, record its average **font size** and whether it is **bold**.

Across the whole document:
6. **Headers/footers removed (LESSONS A6).** Look at the first 3 and last 3 lines of each page; mask digits (so "صفحة 3 من 10" = "صفحة 4 من 10"); a line repeated on ≥50% of pages (min 2) is dropped everywhere.
7. **Heading detection, in order of trust:**
   1. the PDF's own **outline/bookmarks** (`get_toc()`), if present;
   2. **font size**: the most common size (weighted by characters) = body text; every distinct size ≥ 1.15× body (on lines ≤120 chars) is a heading level, biggest = level 1;
   3. **bold** short line (≤80 chars, not ending in `.` or `،`) = one level below the deepest size level;
   4. **Arabic structure words** (regex) = below that.
8. **Paragraph merging (LESSONS A8).** Wrapped lines of one paragraph are joined unless the vertical gap is > 0.6 × font size, or the line starts a numbered clause (`1.`, `٢-`, `أ)`, `أولاً:`).

### 5.3 Arabic heading patterns (`cleanup.py`)
| Rank | Pattern |
|---|---|
| 1 | `الباب …`, `الجزء …` |
| 2 | `الفصل …` |
| 3 | `القسم …` |
| 4 | `المادة / مادة / البند` + number (Latin or Arabic-Indic digits), or `المادة الأولى … العاشرة` |
| 5 | `أولاً: / ثانياً - …` up to `عاشراً` |

Lines longer than 90 chars are never headings. `CLAUSE_START` detects numbered clauses inside a section (`1.`, `٢)`, `أ-`, `أولاً:`).

**Lam-alef detector (LESSONS A1):** counts patterns that almost never appear in correct Arabic (`اال`, `اإل`, `األ`, `اآل`, `عالمة`, a lone ` ال `). 3+ hits → warning: "set `"ocr": true` for this file".

### 5.4 DOCX loader (`docx_loader.py`)
Walks the document body **in order** so paragraphs and tables stay interleaved. Headings, in order:
1. Word style: `Title` → level 0; `Heading N` / `عنوان N` → level N;
2. paragraph outline level → level + 1;
3. short paragraph where every run is bold (not ending in `.`/`،`) → level 7;
4. Arabic structure regex → level 7 + rank.

Tables → `header: value` rows. No pages (citations show file + section).

### 5.5 Markdown, TXT, OCR (`text_loader.py`, `ocr.py`)
- **Markdown:** `#` count = level; `| a | b |` tables (separator row skipped) → `header: value`; bullet markers stripped.
- **TXT:** blank lines separate paragraphs; a line matching the Arabic regex is a heading.
- **OCR, Tesseract** (`OCR_ENGINE=tesseract`, default, offline, ~2 s/page): page rendered at 300 dpi, language `OCR_LANG` (default `ara+eng`; falls back to `eng` if Arabic data is missing). Bidi marks stripped. Headings found only by the Arabic regex (OCR has no font info). Weakness: reads tables column by column (LESSONS C1b).
- **OCR, vision** (`OCR_ENGINE=vision`, ~3 s/page): page rendered at 200 dpi, sent to the vision model with an Arabic prompt: "copy the text as Markdown, headings with #, tables as Markdown tables with header row, don't summarize or add anything". The Markdown then goes through the Markdown loader. Keeps tables.
- `ara+eng` keeps Latin course codes like `CPE201` but sometimes misreads an Arabic word as Latin; `ara` reads Arabic better but drops codes. Test both on scanned Birzeit pages.

### 5.6 Section-based chunking (`sections.py`) — the core idea
**One chunk = one section of the document as its author wrote it.** Not fixed 500-token pieces, not pages.

How: walk the blocks keeping a **stack of open headings**. A heading closes the current section and opens a new one; the stack gives the **breadcrumb** (e.g. `دليل سياسات الموارد البشرية > الفصل الأول: الإجازات > الإجازة السنوية`). Text before the first heading becomes an intro section named after the document. A heading directly followed by a deeper heading has no text, so it only appears in the path.

**Safety net:** a section longer than `MAX_SECTION_CHARS` (2,500) is split at its own **numbered clauses** (falling back to paragraphs), grouping whole clauses; every part keeps the title with `(جزء 1/2)` and the breadcrumb.

**Each chunk (one line in `chunks.jsonl`):**
```json
{"id": "hr_policies_2025.pdf#s1#1", "source": "hr_policies_2025.pdf",
 "doc_title": "دليل سياسات الموارد البشرية", "version": "2025", "date": "2025-01-01",
 "section_title": "الإجازة السنوية", "section_path": "… > الفصل الأول: الإجازات > الإجازة السنوية",
 "page_start": 1, "page_end": 1, "part": 1, "parts": 1, "text": "يستحق الموظف إجازة سنوية …"}
```

**What gets embedded:** `doc_title + " - إصدار " + version` / `section_path` / `text`. The title and breadcrumb are a free human-written summary, which helps retrieval.

**Citation label:** `file، section_title، ص N` (or `ص N-M`; no page part for DOCX/MD/TXT).

**Judge line:** "A section is a unit of meaning the author already defined, like 'المادة 5: الإنذار الأكاديمي'. Fixed-size chunks cut a rule in half; page chunks mix topics. Sections give complete rules and a title we can embed and cite."

### 5.7 Metadata (`data/raw/metadata.json`)
```json
{"file.pdf": {"title": "دليل الطالب", "version": "2025", "date": "2025-09-01", "ocr": false}}
```
`version`/`date` decide conflicts; `ocr: true` forces OCR for a broken text layer.

### 5.8 Build and inspect
- `python -m src.ingest.build_index` → loads every supported file in `DOCS_DIR` (`.pdf .docx .md .txt`), builds sections and chunks, gives each chunk a globally unique id, embeds them, saves `data/index/embeddings.npy` + `chunks.jsonl`.
- `inspect.py` / `scripts/check_extraction.py` show the section tree before paying for embeddings, with warnings: nothing extracted (scanned?), no headings found, lam-alef corruption, chunks still over the limit.

---

## 6. Retrieval in detail (`src/retrieval/`) — Retrieval, 10 pts

### 6.1 Embeddings (`embedder.py`)
`text-embedding-3-large` turns text into 3,072 numbers capturing meaning. Batches of 100 texts per API call. Every vector is **normalized to length 1**, so a plain dot product **is** cosine similarity.

### 6.2 Vector store (`store.py`)
A NumPy matrix, one row per chunk. Search = `scores = vectors @ query_vector`, then sort. Brute force, instant for thousands of chunks. Saved to disk so we embed once, not on every start.
**Judge line:** "FAISS, Chroma, pgvector all do this under the hood. At our size (tens to hundreds of sections) exact search is instant; for millions we'd swap in pgvector/FAISS with HNSW."

### 6.3 Arabic normalization + BM25 (`normalize.py`, `bm25.py`)
Normalization (only for BM25; the original text is kept for display, citations and embeddings):
- remove diacritics (tashkeel) and tatweel (`ـ`)
- `إ أ آ ٱ → ا`, `ى → ي`, `ة → ه`, `ؤ → و`, `ئ → ي`
- lowercase Latin (course codes)

Tokenizer: split into words, strip the definite article `ال` from words longer than 4 letters (`المساق → مساق`), drop ~35 Arabic stopwords (`في، من، على، كم، هل، ما …`).

BM25 (`BM25Okapi`) indexes `doc_title + section_path + text` per chunk. It rewards rare exact tokens (a match on `CPE310` counts far more than on `الطالب`) and short focused chunks.

### 6.4 Hybrid with RRF (`hybrid.py`)
1. dense: top `CANDIDATES` (15) by cosine
2. BM25: top 15 (zero scores skipped)
3. **Reciprocal Rank Fusion:** `score(chunk) = Σ 1 / (RRF_K + rank)` with `RRF_K = 60`, the standard value from the original RRF paper
4. keep top `TOP_K` (4); each chunk carries `{"rrf", "cosine", "bm25"}` scores for the debug panel
5. `best_dense_score` (highest cosine) is returned for the refusal gate

**Judge line:** "Vectors catch meaning and dialect paraphrases; BM25 catches exact tokens like course codes and numbers. Their scores are on different scales, so RRF merges by rank instead of score."

---

## 7. Generation in detail (`src/generation/`) — Grounding & citations, 10 pts

### 7.1 Query rewriting (`rewrite.py`, `prompts.py`)
- Model: `gpt-5-nano`. Input: last 3 turns (6 messages, each cut to 500 chars) + the question.
- Rules (Arabic prompt): dialect → formal Arabic; follow-up → standalone using the history; clear question → keep as is; **don't answer, don't add details**; **never change the topic**; one line only.
- Few-shot examples come from `domain.REWRITE_EXAMPLES`: dialect, follow-up, already-clear, and an **off-topic example that stays off-topic**.
- Deliberately does **not** tell the rewriter the domain. When it did, "كيف أطبخ المقلوبة؟" was bent into a workplace-food-policy question, scored 0.546 and passed the gate (LESSONS B5). After the fix it scored 0.15 and was refused.
- Only the first line of the output is used; empty output falls back to the original question.

### 7.2 Answer prompt (`prompts.py`)
System prompt: "You are {ASSISTANT_NAME}, answering {AUDIENCE} about {DOMAIN_DESCRIPTION}, from the attached sources only", plus numbered rules (in Arabic):
1. Use only the attached sources. No general knowledge, no guessing.
2. After every fact, put the citation exactly as written in the source's "الاستشهاد" line, in square brackets.
3. If the answer isn't in the sources, reply with **only** the fixed refusal sentence.
4. If two versions/documents conflict, use the **newest date** and briefly mention what the older one said.
5. Answer in simple formal Arabic, concise, even if the question was in dialect.
6. + any `domain.EXTRA_RULES`.

Each source is shown as:
```
### المصدر 1
الاستشهاد: [hr_policies_2025.pdf، الإجازة السنوية، ص 1]
الموقع في الوثيقة: … > الفصل الأول: الإجازات > الإجازة السنوية
الوثيقة: دليل سياسات الموارد البشرية - إصدار 2025 (2025-01-01)
<section text>
```
The user message contains both the original question and the rewritten one.

### 7.3 Two-layer refusal
1. **Gate (no LLM call):** if the best cosine < `REFUSAL_THRESHOLD` (0.30), return `domain.REFUSAL_MESSAGE` immediately. Fast, free, catches clearly off-topic questions.
2. **Prompt rule:** catches questions that *sound* on-topic but aren't covered (e.g. "salary of the sales manager"). The answer is marked refused if it contains the first 20 characters of the refusal sentence.

**Judge line:** "A threshold alone can't separate 'sounds related but not covered' from real questions, so the threshold is set safely below every real question and the prompt rule handles the rest. Both layers are measured in the eval."

### 7.4 LLM wrapper (`llm.py`)
- Never sends `temperature` (reasoning models reject it); sends `reasoning_effort` only to `gpt-5*`/`o*` (LESSONS B2).
- `chat_stream()` streams with `stream_options={"include_usage": True}`, so we still get token counts from the last event.

### 7.5 Pipeline (`answer.py`, `RagPipeline`)
Split into three steps so the UI can stream:
- `prepare()` → rewrite → hybrid retrieve → gate decision
- `stream()` → yields the refusal sentence, or streams the grounded answer
- `finish()` → `{answer, refused, sources, debug: {question, search_query, best_cosine, threshold, refused_by_gate, retrieved chunks with scores, tokens, seconds}}`
- `answer()` runs all three (used by the eval and the CLI): `python -m src.generation.answer "سؤال"`.
- Options for experiments: `use_rewrite`, `use_bm25`, `top_k`.

---

## 8. The app (`app/`) — Bonus: working product 5 + RTL 2 + features 3

Run: `streamlit run app/Home.py` (from `template/`).

### 8.1 Shared (`common.py`)
- **RTL CSS** for the whole app; code and tables stay LTR.
- **Login gate** (`require_login`): login form; `role="admin"` blocks other roles. The sidebar with logout is drawn **before** the role check, so a blocked user can still log out (LESSONS E3). `AUTH_ENABLED=false` → logged in as `dev`/admin (development only).
- `load_pipeline()` is cached with `st.cache_resource`, so the index loads once.

### 8.2 Chat (`Home.py`)
- Sidebar: **new chat**, **saved conversations** list, a **settings expander with toggles for query rewriting and hybrid search** (useful for a live before/after demo in front of judges).
- Example question buttons from `domain.EXAMPLE_QUESTIONS`.
- **Input disabled while an answer is being written** (a `pending` flag in session state), so a fast-typing judge can't cancel the running answer (LESSONS E1).
- Answer is **streamed** (`st.write_stream`).
- Under each answer: **📚 sources** (citation, breadcrumb, full section text) and **🔍 "كيف وصلت للإجابة؟"** (rewritten query, best cosine vs threshold, whether the gate refused, table of retrieved chunks with rrf/cosine/bm25 scores, seconds and tokens). Optional `domain.DISCLAIMER`.
- Errors (missing key, network) are shown in the UI, not a crash.
- Question + answer + all debug data are saved to SQLite.

### 8.3 Admin (`pages/1_Admin.py`, admin only)
- **Upload** PDF/DOCX/MD/TXT; new files get default metadata (title from filename, **version guessed from a year in the filename**, today's date, `ocr: false`).
- **Editable metadata table** (title, version, date, OCR flag) → save to `metadata.json`.
- **Rebuild index** button (clears the cached pipeline after).
- **Delete** a document.
- **Section preview**: for any document, shows how it will be chunked (indented by depth, char counts) plus the same warnings as `check_extraction.py`.

### 8.4 Analytics (`pages/2_Analytics.py`, admin only)
- Metrics: number of questions, conversations / users, **refusal rate**, **average latency**.
- Tokens total and per answer; **estimated cost** if `PRICE_INPUT_PER_1M` / `PRICE_OUTPUT_PER_1M` are set in `.env` (left empty by default, so no made-up prices).
- **Questions per day** bar chart.
- **Most-asked questions**, grouped by the normalized *rewritten* query, so different phrasings (dialect/formal) of the same question count together. This is the "dashboard of most-repeated questions" bonus idea from problem #1.
- **Unanswered questions = content gaps**: every refused question, so the university knows which documents are missing.

---

## 9. Storage (`src/storage/db.py`)
SQLite at `data/app.db`, foreign keys on, cascade delete.
```
conversations(id, username, title, created_at)
messages(id, conversation_id, role, content, refused, seconds, input_tokens,
         output_tokens, search_query, sources_json, created_at)
index idx_messages_conv on messages(conversation_id)
```
Assistant messages store the answer's metadata (refused, seconds, tokens, rewritten query, sources + debug JSON), which is exactly what analytics reads. Conversations are listed and deleted per username only.

---

## 10. Security (`src/auth.py`, config) — Code & engineering: security & scaling
- **Keys only in `.env`** (git-ignored). `.env.example` documents every variable with empty secrets. `openai_client.py` raises a clear error if the key is missing.
- **Users** live in `.env` as `AUTH_USERS="name:role:hash,…"`. Make an entry with `python scripts/hash_password.py` (password typed with `getpass`, never echoed).
- **Hash format:** `pbkdf2$200000$<salt b64>$<digest b64>`: PBKDF2-HMAC-SHA256, 200,000 iterations, random 16-byte salt. Compared with `hmac.compare_digest` (constant time).
- **Roles:** `admin` (documents, analytics) and `user` (chat).
- **Data stays local:** documents, index and history are local files + SQLite. Only the question and the retrieved sections go to OpenAI.
- `.gitignore` also excludes the built index, the DB and eval results.
- **Scaling story (README):** NumPy store → pgvector/FAISS; SQLite → Postgres; one index per tenant (per university); cost ≈ tokens per answer × price.
- Honest limits (said in `auth.py`): for a real product, move users to the DB and add rate limiting / SSO.

---

## 11. Configuration (`config.py` + `.env`)
| Setting | Default | Meaning |
|---|---|---|
| `DOCS_DIR` | `data/raw` (`.env` currently `data/examples`) | documents folder |
| `OPENAI_API_KEY` | — | required |
| `OPENAI_CHAT_MODEL` | `gpt-5.4-mini` | answers |
| `OPENAI_REWRITE_MODEL` | `gpt-5-nano` | rewrite |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-large` | embeddings |
| `OPENAI_JUDGE_MODEL` | chat model | eval judge |
| `OPENAI_VISION_MODEL` | chat model | vision OCR |
| `OPENAI_REASONING_EFFORT` | `low` | reasoning models only |
| `PRICE_INPUT_PER_1M` / `PRICE_OUTPUT_PER_1M` | empty | cost estimate in analytics |
| `OCR_ENGINE` | `tesseract` | or `vision` |
| `OCR_LANG` | `ara+eng` | Tesseract languages |
| `MIN_TEXT_CHARS` | 20 (code) | fewer chars on a page = scanned |
| `MAX_SECTION_CHARS` | 2500 | split long sections above this |
| `TOP_K` | 4 | sections given to the LLM |
| `CANDIDATES` | 15 | per method before fusion |
| `RRF_K` | 60 | RRF constant |
| `REFUSAL_THRESHOLD` | 0.30 | gate; calibrate with `--calibrate` |
| `AUTH_ENABLED` | true | false = no login (dev) |
| `AUTH_USERS` | empty | `name:role:hash,…` |

### `domain.py` (everything problem-specific)
`ASSISTANT_NAME`, `DOMAIN_DESCRIPTION`, `AUDIENCE`, `REFUSAL_MESSAGE` (also used to detect refusals), `DISCLAIMER`, `EXTRA_RULES`, `APP_TITLE`, `APP_ICON`, `APP_SUBTITLE`, `EXAMPLE_QUESTIONS`, `REWRITE_EXAMPLES`.

---

## 12. Evaluation (`eval/`) — Evaluation 5 pts + tie-break #2

### 12.1 Question format (`questions.jsonl`, one JSON per line)
```json
{"id": "q11", "type": "multi-turn",
 "history": [{"role": "user", "content": "…"}, {"role": "assistant", "content": "…"}],
 "question": "وإذا كانت المهمة داخل فلسطين؟", "gold_answer": "80 شيكل يوميا.",
 "gold_sources": [{"source": "travel_policy.docx", "section": "المياومات"}],
 "expect_refusal": false}
```
Gold source matched by part of the section title/path, or by `page` within the chunk's page range.

### 12.2 Metrics (`run_eval.py`)
| Metric | Meaning | Over |
|---|---|---|
| Hit@k | at least one retrieved section is a gold one | answerable |
| Precision@k | share of the k retrieved sections that are gold | answerable |
| Refusal accuracy | refused exactly when expected | all |
| Correct | LLM judge: agrees with the gold answer | answerable |
| Faithful | LLM judge: every claim supported by the retrieved text | answerable |
| Cited | answer contains a `[….pdf/docx/md/txt …]` citation (regex) | answerable |
| avg seconds / tokens | latency and cost proxy | all |

The judge prompt (Arabic) returns `{"correct", "faithful", "reason"}` as JSON.

### 12.3 Commands
```
python eval/run_eval.py                full system        → eval/results/full.json
python eval/run_eval.py --dense-only   no BM25            → dense_only.json
python eval/run_eval.py --no-rewrite   no rewriting       → no_rewrite.json
python eval/run_eval.py --calibrate    retrieval only; prints each question's best cosine,
                                       suggests threshold = lowest in-scope − 0.07, and warns
                                       if out-of-scope questions overlap real ones
```
Every run also prints a **failure list** (wrong refusal, miss, or incorrect) for the README failure analysis.

### 12.4 Current eval set (fictional example docs, 14 questions)
lookup (PDF, DOCX, MD), table (PDF, DOCX), long split section, 2 version conflicts (2025 PDF vs 2023 TXT), 2 dialect, 1 multi-turn, 3 out-of-scope (cooking, a salary, health insurance).

### 12.5 Saved results (`eval/results/full.json`, full system)
| Hit@4 | Precision@4 | Refusal acc. | Correct | Faithful | Cited | Avg time | Avg tokens |
|---|---|---|---|---|---|---|---|
| 1.00 | 0.295 | 1.00 | 1.00 | 1.00 | 1.00 | 3.14 s | 1,389 |

Best cosine per question in that run: in-scope 0.381 (multi-turn) to 0.620; out-of-scope 0.150 (cooking, refused by the gate), 0.306 and 0.355 (salary, insurance: passed the gate, refused by the prompt rule).

- Precision@4 is low by design: each question has ~1 gold section, so at most 1 of 4 retrieved is "gold" (LESSONS D4). Report **Hit@k** as the main retrieval metric.
- From the demo (LESSONS D2): turning rewriting off dropped correctness from 100% to 82%. Dense-only vs hybrid showed no difference on a tiny corpus (D3); hybrid's value shows on exact codes.
- ⚠️ The README's eval note quotes slightly different cosines (in-scope ≥ 0.417; out-of-scope 0.150 / 0.306 / 0.376) from an earlier run. The README gets rewritten with Birzeit numbers anyway.
- No `--dense-only` / `--no-rewrite` result files are saved yet: the before/after table still needs to be produced on the Birzeit docs.

---

## 13. Scripts and the switch-to-Birzeit checklist

| Script | What it does |
|---|---|
| `scripts/check_extraction.py [folder|file] [--text]` | section tree, citation labels, sizes, `[split]` marks, warnings. **Run first.** |
| `scripts/list_models.py` | lists `gpt-*`, `o*`, `text-embedding*` models available to the key |
| `scripts/hash_password.py` | prints a `name:role:hash` entry for `AUTH_USERS` |
| `scripts/make_examples.py` | regenerates the 4 fictional docs (PDF via headless Chrome with ligatures off, DOCX with styles + table, MD, TXT with `المادة N` and an older conflicting rule) |

**Switch steps (from the README quickstart):**
1. Birzeit PDFs → `data/raw/` + `metadata.json` (title, version, date, ocr). Set `DOCS_DIR=data/raw` in `.env`.
2. `python scripts/check_extraction.py` → read the section tree; lam-alef warning → `"ocr": true`; tables wrong in scans → `OCR_ENGINE=vision`.
3. Edit `domain.py`: المرشد الذكي, audience (طلبة جامعة بيرزيت والمرشدون الأكاديميون), refusal sentence, disclaimer (e.g. "confirm with your advisor/registrar"), example questions, rewrite examples that **keep course codes and terms as-is** (LESSONS B6).
4. `python -m src.ingest.build_index`
5. Write ≥12 Birzeit eval questions **before tuning** (lookups, course-code/prerequisite tables, ≥2 dialect, ≥2 out-of-scope, 1 conflict, 1 multi-turn).
6. `--calibrate` → set `REFUSAL_THRESHOLD` → full / `--dense-only` / `--no-rewrite` for the before/after table.
7. `hash_password.py` → users in `.env`.
8. `streamlit run app/Home.py`; delete `data/examples/` (or keep as sample data); fill the README.

---

## 14. Lessons already built into the template
From `docs/LESSONS_LEARNED.md`, the ones the template handles:

| Lesson | Problem | Where it's handled |
|---|---|---|
| A1 | lam-alef ligature extracts as wrong letters | detector + warning (`cleanup.py`, `inspect.py`), OCR override |
| A2 | numbers/punctuation misplaced in RTL lines | word-position RTL rebuild + `tidy()` |
| A3 | tables come out glued/reversed | cell boxes + words + row reversal + `header: value` |
| A5 | mirrored parentheses | `tidy()` regexes |
| A6 | headers/footers in every chunk | repeated-line removal |
| A8 | each wrapped line became a paragraph | gap-based paragraph merging |
| A9 | year jumps before the period | `tidy()` |
| A10 | bold table headers became sections | tables removed before heading detection |
| B2 | reasoning models reject params | `llm.py` `_params()` |
| B3 | slow answers | `gpt-5.4-mini` + streaming (3.1 s avg) |
| B4/B5 | rewriter adds details / pulls off-topic into domain | few-shot examples, no domain in rewrite prompt |
| C1b | OCR bidi marks, Latin vs Arabic trade-off | marks stripped; `OCR_LANG` setting; vision option |
| D1 | threshold can't catch everything | two-layer refusal + `--calibrate` |
| D2 | dialect/follow-ups fail | rewrite step |
| E1 | fast typing cancels the answer | input disabled while busy |
| E3 | blocked user can't log out | sidebar drawn before role check |
| F2 | problems invisible without inspecting | debug panel, check script, CLI |

Still open / to watch: A4 (diacritics noise), B6 (rewriter swaps key terms for synonyms), C2 (dev server can't start from `~/Desktop` in the Claude app; run from terminal), D5 (chunks are sections, so this is mostly gone), E2 (test upload by hand), E4 (reload logs you out; history is kept).

---

## 15. How the template maps to the rubric

| Rubric item | Pts | What in the template earns it |
|---|---|---|
| Data prep | 5 | 4 loaders, Arabic PDF fixes, OCR fallback, tables as `header: value`, header/footer removal, section chunking, metadata, extraction checker |
| Retrieval | 10 | embeddings + BM25 with Arabic normalization + RRF, query rewriting, per-chunk scores visible |
| Grounding & citations | 10 | sources-only prompt, `[file، section، page]` after every fact, two-layer refusal, newest-version conflict rule |
| Evaluation | 5 | eval set with gold sections, Hit/Precision@k, refusal accuracy, LLM-judge correct/faithful, cited, latency, tokens, calibrate + ablations, failure list |
| Code & engineering | 15 | separate layers, all config in `.env`, pinned requirements, README run steps, hashed logins, no secrets in code |
| Innovation | 5 | dialect rewriting, "how I got this answer" transparency panel, content-gap analytics |
| Bonus | +10 | working Streamlit product, Arabic RTL, login + roles, admin upload/rebuild, saved history, analytics |

Not covered by the template (Aboud's side): problem evidence, business plan, marketing, deck, demo video.

---

## 16. Judge Q&A cheat sheet

- **"Explain your chunking."** One chunk per document section, found from PDF outline, font sizes, bold lines, Word heading styles, Markdown `#`, and Arabic structure words like المادة / الفصل. Long sections split at their numbered clauses and keep the title.
- **"Why hybrid search?"** Vectors find meaning and dialect paraphrases; BM25 finds exact course codes and numbers. RRF merges them by rank because their scores aren't comparable.
- **"How do you stop hallucination?"** Sources-only prompt, mandatory citations, a similarity gate before the LLM, and a fixed refusal sentence. Faithfulness is measured by an LLM judge.
- **"How do you handle dialect?"** A small model rewrites the question to formal Arabic before retrieval; it's told never to change the topic so off-topic questions still get refused.
- **"Conflicting documents?"** Every source carries its version and date; the model uses the newest and mentions the older rule.
- **"Scanned PDFs?"** Pages with no text layer go to Tesseract or a vision model that keeps tables. Broken Arabic text layers are detected (lam-alef check) and routed to OCR.
- **"Why not a vector database?"** At our size, a NumPy matrix multiply is exact and instant; the store is one class, so swapping in pgvector/FAISS is a contained change.
- **"Security?"** Keys in `.env` only, salted PBKDF2 password hashes compared in constant time, admin pages role-protected, data stays on our server except what's sent to OpenAI to answer.
- **"How did you evaluate?"** Questions written before tuning, with gold sections; Hit@k, refusal accuracy, correctness, faithfulness, citations, latency, tokens; ablations without BM25 and without rewriting.
- **"Did you use AI?"** Yes, Claude Code; logged in `AI_USAGE.md` and disclosed in the README. Libraries are listed; no code copied from other projects.

---

## 17. Attribution and AI disclosure (as in the README)
- AI: **Claude Code (Claude Opus 5.5)** prepared the template the night before from the team's design; adapted during the hackathon. Log: `template/AI_USAGE.md`.
- Libraries: OpenAI Python SDK, PyMuPDF, python-docx, rank-bm25, NumPy, Streamlit, python-dotenv, pytesseract / Tesseract OCR, Pillow.
- RRF constant 60 is from the original Reciprocal Rank Fusion paper (Cormack et al., 2009).
- No code copied from other projects. `demo/` was learning material only.
