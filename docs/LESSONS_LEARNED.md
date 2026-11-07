# Lessons Learned: problems we hit and how we solved them

Every problem met while building the practice demo (`demo/`, Nov 6), the hackathon template (`template/`, Nov 7 early morning), and during the hackathon itself, with the fix.
✅ = already handled in `template/`.
**Read this before building. Add every new problem the moment you solve it.**

Format: **Symptom** (what you see) → **Cause** → **Fix** → **Tomorrow** (what to do differently).

---

## A. Arabic PDF text extraction (the biggest time sink)

### A1. Letters come out wrong around "لا" (lam-alef) ✅ detected in template
- **Symptom:** `علامة` extracts as `عالمة`, `الامتحان` as `االمتحان`, `لا يجوز` as `ال يجوز`, `الإنذار` as `اإلنذار`.
- **Cause:** the PDF draws لا as one combined glyph (a ligature) and maps it back to the wrong letters. It happened with every font we tried, and with both PyMuPDF and `pdftotext`.
- **Fix (demo):** we controlled the PDFs, so we generated them with ligatures off (`font-feature-settings: 'rlig' 0`).
- **Tomorrow:** you won't control the organizers' PDFs. **In the first 10 minutes, print the extracted text of every PDF and grep for `عالمة`/`اال`/` ال ` patterns.** If affected: (1) ask organizers for the source .docx; (2) OCR those pages instead (needs Arabic Tesseract, see C1); (3) as a last resort, have an LLM clean each page's text before chunking.

### A2. Numbers and punctuation end up in the wrong place in a line ✅
- **Symptom:** `%15 لا يجوز أن تتجاوز نسبة غياب الطالب` instead of `لا يجوز أن تتجاوز نسبة غياب الطالب 15%`. Periods jump to the line start.
- **Cause:** PDFs store text in *visual* order; mixing RTL Arabic with LTR numbers scrambles it.
- **Fix:** extract **words with positions** (`page.get_text("words")`), group by (block, line), **sort each line by x descending** (right-to-left), and join. Then tidy up: `%15`→`15%`, remove the space before `. : ،`. See `demo/src/ingest/loaders.py` → `extract_page_text()`, `_tidy()`.
- **Tomorrow:** reuse this loader logic as-is.

### A3. Tables come out as glued garbage ✅
- **Symptom:** `CPE201هياكل البيانات3`, headers lost. PyMuPDF's `table.extract()` returned Arabic **with the characters reversed** (`تانا يبلا لكا يه`).
- **Fix:** use `page.find_tables()` **only for the table's position and cell boxes**, then collect the words inside each cell box and sort them RTL. Write each row as `header: value | header: value`. Cells come left-to-right, so reverse each row. See `table_to_text()`.
- **Tomorrow:** the same function works; check one table's output by eye.

### A4. Diacritics (tashkeel/tanween) get lost or misplaced
- **Symptom:** `أسبوعياً` → `أسبوعي` (the `ًا` vanished), `يُحرم` → `ُيحرم`.
- **Fix:** strip diacritics in normalization (we do for BM25). In the demo we simply left them out of the sample text.
- **Tomorrow:** expect this noise in real docs. It mostly doesn't hurt retrieval, but don't be surprised by it in the displayed source text.

### A5. Parentheses come out mirrored ✅ regex in template
- **Symptom:** `المادة (1):` → `المادة 1( ):`
- **Fix (demo):** avoided parentheses in the sample docs.
- **Tomorrow:** if it appears in their docs, add a small regex in `_tidy()`, e.g. `(\d+)\( \)` → `(\1)`. Low priority; the LLM reads it fine.

### A6. Repeated headers/footers end up in every chunk ✅ removed in template
- **Symptom:** our disclaimer line ("وثيقة تجريبية خيالية...") is inside every page's chunk. Real documents have the same issue with headers, footers and page numbers.
- **Fix (not done in demo):** before chunking, drop lines that appear on more than ~50% of pages of the same file.
- **Tomorrow:** implement this if the organizers' docs have headers/footers (likely).

### A7. PyMuPDF's HTML→PDF writer can't produce clean Arabic
- **Symptom:** PDFs made with `page.insert_htmlbox()` extracted as broken presentation-form letters (`ﺟﺎﻣﻌﺔ ﺍǄﻨﺨﻴﻞ`).
- **Fix:** generate Arabic PDFs by rendering HTML with **headless Chrome** (`--print-to-pdf`). See `demo/scripts/make_sample_pdfs.py`.
- **Tomorrow:** only relevant if we must create our own sample PDFs.

### A8. Every wrapped line of a PDF paragraph became its own paragraph
- **Symptom:** a clause "1. يحق للموظف..." split into 3 text blocks (one per visual line).
- **Cause:** Chrome-made PDFs put each line in its own PDF text block, so grouping by block doesn't find paragraphs.
- **Fix ✅:** merge consecutive lines unless the vertical gap is larger than 0.6× the font size, or the line starts a numbered clause (`pdf_loader.py`).

### A9. A year at the end of a line jumps before the period
- **Symptom:** `ابتداء من الأول من كانون الثاني.2025`
- **Fix ✅:** `tidy()` moves a trailing number back before the period: `الثاني 2025.`

### A10. Section detection: what worked (tested on PDF, DOCX, MD, TXT + the demo's PDFs)
- PDF headings by **font size** worked with no keywords (body 9.0 pt; headings 16.5 / 12.8 / 10.5 pt became levels 1/2/3).
- Table header cells are bold too, so tables are cut out **before** heading detection, or every column header would become a section.
- A TXT file has no font info: only `المادة / الفصل / أولاً` patterns are detected. Its first title line becomes part of an intro section named from `metadata.json`.
- Forcing OCR on a lam-alef-broken PDF gave perfect text (Tesseract and vision both), and the `المادة` headings were found again by regex.

### A11. The organizers' regulation PDFs store every Arabic word reversed ✅ (Nov 7)
- **Symptom:** `get_text()` on `أنظمة وتعليمات منح درجة البكالوريوس للعام 2025.pdf` gives `ةساردلا ماظن :ىلوألا ةداملا`. Every regulation PDF in the zip is a ReportLab render made by the organizers' scraper.
- **Fix:** the zip also has the clean text (`json/documents.jsonl`, `text/*.txt`). Index the text, and recover pages by matching each paragraph's words against each PDF page's words (each PDF word added forwards AND reversed). A greedy "best page per paragraph" jumped from page 2 to 9 on one noisy paragraph; a monotonic dynamic-programming alignment (pages never go backwards, maximize total overlap) gave clean pages 1→11. Pages are written as `[[page N]]` lines that `text_loader` reads.
- **Next time:** always check whether a dataset ships a text twin before fighting the PDF.

### A12. PyMuPDF's layout model segfaulted inside `find_tables()` ✅ (Nov 7)
- **Symptom:** index build died with exit 139 and no output (stdout was buffered). `python -u -X faulthandler` showed the crash in `pymupdf/layout/onnx/...` called from `find_tables`, on the EE study plan.
- **Fix:** `page.find_tables(use_layout=False)`. Line-based detection is enough for ruled tables.
- **Next time:** run long jobs with `-u -X faulthandler` so a native crash says where it happened.

### A13. Articles past the tenth weren't headings ✅ (Nov 7)
- **Symptom:** `المادة الحادية عشرة: التحذير الأكاديمي` and every later article merged into article 10; the probation answer cited "المادة العاشرة".
- **Fix:** an extra pattern for any ordinal `المادة ال... (عشرة|والعشرون...):` with a colon required. Bachelor regulations went from 11 to 17 sections.

### A14. Lam-alef in the real guide ✅ partly (Nov 7)
- **Symptom:** the 625-page guide extracts `الأكاديمي` as `األكاديمي` and `لا` as `ال`.
- **Fix:** safe display repairs only (`األ/اإل/اآل` never occur in correct Arabic; a lone `ال` is always `لا`). Ambiguous cases (`عالمة`) are left alone, and BM25 normalization maps `لا`→`ال` on both sides so they still match. OCR of 625 pages was too slow for the day.

---

## B. LLM / OpenAI

### B1. Model names and SDK version were newer than expected
- **Symptom:** OpenAI SDK installed as v3.x, and many new model names exist.
- **Fix:** list what the key can actually use before choosing:
  `client.models.list()`, then pick. The demo uses `gpt-5-mini` (answers), `gpt-5-nano` (rewrite), `text-embedding-3-large`.
- **Tomorrow:** run the model list first; put model names in `.env`, never hard-coded.

### B2. Reasoning models reject some parameters
- **Cause:** gpt-5* / o* models don't accept a custom `temperature`, and non-reasoning models don't accept `reasoning_effort`.
- **Fix:** never send `temperature`; send `reasoning_effort="low"` only when the model name starts with `gpt-5` or `o`. See `demo/src/generation/llm.py`.

### B3. Answers are slow (5–8 s)
- **Cause:** two LLM calls per question (rewrite + answer) on a reasoning model.
- **Fix in place:** `reasoning_effort=low`. **Not yet tested:** faster models (e.g. `gpt-5.4-mini`/`nano`, `gpt-4.1-mini`), streaming the answer to the UI, skipping rewrite on the first turn when the question is already formal Arabic.
- **Tomorrow:** a judge watching an 8 s spinner is fine, but 20 s isn't. Measure `avg_seconds` in the eval.
- **Measured Nov 7 ✅:** same question, answer model only: `gpt-5-mini` 5.2 s, `gpt-5.4-mini` 3.7 s, `gpt-4.1-mini` 3.1 s, all with the same correct answer. The template defaults to `gpt-5.4-mini` and **streams** the answer. Template eval average: 3.1 s per question (demo: 5.4 s).

### B4. The rewriter sometimes adds things to the query ✅ few-shot examples in template
- **Symptom:** `كيف أطبخ المقلوبة؟` was rewritten to include "...وما المعايير التي تؤثر في نجاح تحضيره؟", invented detail.
- **Fix:** the prompt already says "don't add information". It's harmless for retrieval here, but watch the "search query" in the debug panel.
- **Tomorrow:** if retrieval drifts, tighten the rewrite prompt or show the model 1–2 examples.

### B5. Telling the rewriter the domain pulled off-topic questions INTO the domain
- **Symptom:** "كيف أطبخ المقلوبة؟" was rewritten to "ما هي سياسات الموارد البشرية المتعلقة بإعداد الطعام في مكان العمل..." It scored 0.546 and **passed the refusal gate**. The LLM still refused (layer 2), but layer 1 was defeated.
- **Cause:** the rewrite prompt said "for searching in [domain]", so the model bent every question toward the domain.
- **Fix ✅:** the rewrite prompt doesn't mention the domain, says "never change the topic", and has an off-topic few-shot example. After the fix, the same question scored 0.15 and was refused by the gate.
- **Tomorrow:** after editing `domain.py`, run `eval/run_eval.py --calibrate` and check that out-of-scope questions keep their meaning in the "query" column.

### B6. The rewriter swaps domain terms for synonyms
- **Seen:** "المياومة" was rewritten as "الأجر اليومي". Retrieval still worked (thanks to embeddings + the original question in the prompt), but BM25 lost the exact word.
- **Tomorrow:** if the domain has key terms, add a rewrite example in `domain.py` that keeps them as-is.

---

## C. Environment / tooling

### C1. Tesseract had no Arabic language data ✅ fixed Nov 6
- **Symptom:** `tesseract --list-langs` showed only `eng osd snum`. OCR of Arabic scans would return garbage or nothing.
- **Fix:** `brew install tesseract-lang` (686 MB, all languages). Installed on Aboud's Mac; `ara` now listed.
- **Tomorrow:** teammates' laptops need it too if they'll run OCR. Install before leaving home.
- **Vision OCR tested ✅** (`OCR_ENGINE=vision`): about 3 s/page, clean text with headings. One tiny invented letter (`يلتزم` → `يلتزمه`), so still check the output.

### C1b. OCR works but has its own error patterns (tested on a fake scanned page)
- **Result:** ~2 s per page at 300 dpi, and the text is mostly right. A page with no text layer is detected automatically and sent to OCR.
- **Language trade-off:**
  - `ara+eng` keeps Latin course codes (`CPE201`) but sometimes reads an Arabic word as Latin: `كلية` → `AUS`.
  - `ara` reads Arabic words correctly but **drops Latin codes completely** (`CPE201` → `01`).
  - It's now a setting: `OCR_LANG` in `.env` (default `ara+eng`). **Test both on their scanned docs.**
- **Invisible direction marks:** Tesseract wraps Latin text in `‎…‏`. They break exact-match search. **Fix:** stripped in `ocr_page()`.
- **Small misreads:** `أردنيا،` → `أردنياء`, `10%` → `%10`, `وثيقة` → `وثيقه`. Normalization (ة→ه) absorbs some of these for BM25.
- **Tables lose their rows:** OCR reads tables **column by column** (all codes, then all names), so you can't tell which code goes with which course. **If their scanned docs have tables:** use a vision LLM (send the page image, ask for rows as `header: value`) instead of Tesseract for those pages.

### C2. The Claude app couldn't start the dev server from the Desktop folder
- **Symptom:** `preview_start` failed with `Operation not permitted` (macOS privacy protection on `~/Desktop`).
- **Fix:** start the server from the terminal (`.venv/bin/streamlit run app/streamlit_app.py`) and open `http://localhost:8501` in the browser pane.
- **Tomorrow:** same workaround, or put the project outside `~/Desktop` (e.g. `~/code/...`).

### C3. Python packages are newer than examples online
- **Symptom:** numpy 2.x, pymupdf 2.x, streamlit 1.67, openai 3.x; also `import fitz` is deprecated (use `import pymupdf`).
- **Fix:** pin exact versions in `requirements.txt` (done in demo) and use `uv` for a fast, clean venv.

---

## D. Retrieval / refusal behaviour

### D1. A similarity threshold alone can't catch every out-of-scope question
- **Symptom:** "من هو رئيس جامعة النخيل؟" scored 0.441 and "كم رسوم السكن الجامعي؟" 0.413, **higher than a real question** (0.397). They sound on-topic.
- **Fix:** two layers. (1) Gate: refuse without calling the LLM if best cosine < threshold (catches clearly off-topic; ours is 0.30). (2) Prompt rule: a fixed refusal sentence when the chunks don't contain the answer (catches the on-topic-sounding ones). Both test questions were correctly refused.
- **Tomorrow:** set the threshold **below the lowest in-scope question's score** from the eval. Never tune it to block on-topic-sounding questions; that's the prompt's job.

### D2. Dialect and follow-up questions fail without query rewriting
- **Symptom:** with rewriting off, "إذا انسحبت من مادة بالأسبوع التاسع شو بصير؟" retrieved wrong chunks, and "وكم ساعة معتمدة إله؟" scored 0.178 and got refused. Correctness dropped from 100% to 82%.
- **Fix:** keep the rewrite step (dialect → formal Arabic, follow-up → standalone question using the chat history).

### D3. BM25 showed no gain on a tiny corpus
- **Symptom:** dense-only scored exactly like hybrid on 11 chunks.
- **Not a bug:** hybrid helps with exact tokens (e.g. "رمز W": vectors ranked the wrong doc first, BM25 got it right) and as the corpus grows.
- **Tomorrow:** if a judge asks, say this honestly and show the exact-token example. Add eval questions with codes/symbols to measure it.

### D4. Precision@k looks low (0.50) even when everything works
- **Cause:** with few chunks, only 1–2 of the top 4 come from the gold page and the rest are neighbours.
- **Tomorrow:** report Hit@k as the main retrieval metric, explain Precision@k.

### D5. Chunks never cross a page boundary
- **Trade-off:** every chunk has one page to cite, but a sentence that continues onto the next page is split.
- **Tomorrow:** acceptable. If an answer is cut at a page break, add a small cross-page overlap.

### D6. Graduate regulations outranked the bachelor rule ✅ (Nov 7)
- **Symptom:** "قديش لازم يكون معدلي عشان ما آخذ إنذار؟" answered with the master's (2.33) or PhD (2.67) probation GPA instead of the bachelor 2.00. Eval correct = 0.77.
- **Fix:** Checkmate serves undergraduates, so graduate-only documents are not imported (`domain.GRADUATE_TITLE_WORDS`), plus a prompt rule "assume bachelor". Watch out: a filter on "الماجستير" also dropped the certificate document titled "(البكالوريوس أو الماجستير)", so keep titles that also say البكالوريوس.

### D7. Course codes: embeddings miss them and the old guide is outdated ✅ (Nov 7)
- **Symptom:** "شو المتطلب السابق لمساق ENCS3350؟" got the 2024-25 guide's old prerequisites or a refusal.
- **Fix:** exact lookup: a course code in the question adds that course's row from the 2026 plan JSON as a cited source (and skips the score gate). Eval: Hit@4 1.00, refusal accuracy 1.00.

---

## E. UI (Streamlit)

### E1. Sending a new message while an answer is running loses that answer ✅ input disabled in template
- **Symptom:** the first answer disappeared from the chat; only the second showed.
- **Cause:** Streamlit reruns the script on new input and cancels the run in progress.
- **Fix (not done in demo):** keep a `busy` flag in `st.session_state` and pass `disabled=busy` to `st.chat_input`, or append the user message only after the answer is ready.
- **Tomorrow:** implement this, since a judge will type fast during the live test.

### E2. File upload in the UI couldn't be tested automatically
- The browser automation can't drive the file picker. **Tomorrow:** test the upload button by hand before the demo.

### E3. A user blocked from the admin page had no logout button
- **Cause:** the role check stopped the page before the sidebar (with the logout button) was drawn.
- **Fix ✅:** draw the sidebar first, then check the role (`app/common.py`).

### E4. Reloading the page or typing a URL logs you out
- **Cause:** Streamlit keeps the login in the browser session; a reload or a typed URL starts a new session. Chat history is NOT lost (it's in SQLite).
- **Tomorrow (demo day):** navigate with the sidebar links, not the address bar. Log in before the judges arrive.

---

## F. Process

### F1. Leftover test files ended up in the project folder
- A quick test wrote `t.html`/`t.pdf` into `demo/` because a `cd` to a temp folder silently failed. Cleaned up.
- **Tomorrow:** check `git status` before every commit, and keep scratch tests out of the repo.

### F2. Always look at intermediate output
- Most of the problems above were invisible until we **printed the extracted text, the chunks, and the retrieval scores**. The UI's "كيف وصلت للإجابة؟" panel and `python -m src.generation.answer "..."` exist for exactly this.

### F3. Native pptxgenjs charts disappeared when the deck was opened in Keynote
- **Symptom:** the bar chart (projections) and doughnut (budget) rendered as empty space in Keynote's PDF export; the file still passed validation.
- **Cause:** Keynote's PPTX import didn't render those generated charts (Google Slides import of generated charts is also unreliable).
- **Fix:** drew both charts with plain shapes and text boxes in the deck script, so they look the same in PowerPoint, Keynote and Google Slides.
- **Next time:** for a deck that will be imported into Google Slides/Keynote, draw simple charts as shapes, and always render and look at every slide before sharing.
