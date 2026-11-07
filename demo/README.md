# Learn RAG: a small, complete Arabic RAG system

A working question-answering assistant for a **fictional** university ("جامعة النخيل"). Students ask in Arabic (formal or dialect), and the system answers **only from the university's PDFs**, cites the file and page, and refuses when the answer isn't there.

It's built to be read. Every file is short, does one job, and has comments explaining *why*. Read this README top to bottom once, then open the files as each milestone tells you to.

> All documents in `data/raw/` are made up for learning. The university, its rules and its fees do not exist.

---

## Part 1: The big picture

### What is RAG?
**RAG = Retrieval-Augmented Generation.** Think of an **open-book exam**:

- A plain LLM (ChatGPT with no documents) answers from memory. It has never seen *your* university's rules, so it guesses, and guesses confidently. That's called **hallucination**.
- A RAG system first **looks up** the relevant pages in your documents (*retrieval*), then gives those pages to the LLM and says "answer using only this" (*augmented generation*).

You get answers that are specific to your documents, up to date (just add a new PDF, no retraining), and **checkable**, because every answer points to the page it came from.

### The flow, in headlines
RAG has two phases. You run the first **once**, and the second **for every question**.

```
 PHASE A: INDEXING (once, offline)                 python -m src.ingest.build_index

   PDFs ──► 1. Load ──► 2. Normalize ──► 3. Chunk ──► 4. Embed ──► saved index
            text per     clean Arabic      small        vectors     (data/index/)
            page         variants          pieces       of meaning


 PHASE B: ANSWERING (every question)               streamlit run app/streamlit_app.py

   question ──► 6. Rewrite ──► 5. Retrieve ──► 7. Gate ──► 8. Generate ──► answer
   (+ chat      dialect →      hybrid:         too far      LLM answers     + sources
    history)    formal,        vectors +       from docs?   only from the   + citations
                fill in        keywords        → refuse     chunks, cites
                follow-ups                                   them

                9. UI shows it all          10. Eval measures it all
```

1. **Load:** read each PDF page into text, fixing Arabic extraction problems and keeping tables readable.
2. **Normalize:** make spelling variants of Arabic words identical (أ/إ/ا, ى/ي, diacritics...).
3. **Chunk:** cut pages into small pieces, each labeled with its file, page and version.
4. **Embed:** turn each chunk into a vector (a list of numbers representing its meaning) and save it.
5. **Retrieve:** find the chunks closest to the question, by meaning (vectors) and by keywords (BM25).
6. **Rewrite:** before searching, turn dialect into formal Arabic and make follow-up questions self-contained.
7. **Gate:** if nothing in the documents is even close, refuse without asking the LLM.
8. **Generate:** the LLM writes the answer from the retrieved chunks only, with citations.
9. **UI:** an Arabic chat that shows the answer, its sources, and how it got there.
10. **Evaluate:** a fixed set of test questions with known answers, scored automatically.

(Steps 5 and 6 are numbered in the order you'll learn them; at runtime, rewrite happens before retrieve.)

### Map of the code
```
demo/
├── config.py                    every setting ("knob") in one place
├── data/raw/                    the 4 fictional PDFs + metadata.json (version/date of each)
├── data/index/                  built by step A (chunks.jsonl + embeddings.npy)
├── scripts/make_sample_pdfs.py  how the fictional PDFs were generated
├── src/
│   ├── ingest/                  PHASE A
│   │   ├── loaders.py           1. Load
│   │   ├── normalize.py         2. Normalize
│   │   ├── chunking.py          3. Chunk
│   │   └── build_index.py       runs 1→4 and saves the index
│   ├── retrieval/
│   │   ├── embedder.py          4. Embed
│   │   ├── store.py             4. Vector store (search by similarity)
│   │   ├── bm25.py              5. Keyword search
│   │   └── hybrid.py            5. Combine both (RRF)
│   ├── generation/
│   │   ├── rewrite.py           6. Rewrite
│   │   ├── prompts.py           8. The instructions given to the LLM
│   │   ├── llm.py               small wrapper around OpenAI chat
│   │   └── answer.py            PHASE B: rewrite → retrieve → gate → generate
│   └── openai_client.py         shared OpenAI client (key from .env)
├── app/streamlit_app.py         9. The chat UI
└── eval/                        10. questions.jsonl + run_eval.py + results/
```

---

## Part 2: Run it

```bash
cd "/Users/aboudfialah/Desktop/RAG Hackathon/demo"
```

First time only: create the environment and install packages (`uv` is already installed on this Mac).

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
```

Put your OpenAI key in `.env` (copy `.env.example` → `.env`, then fill in `OPENAI_API_KEY`). `.env` is git-ignored, so the key never gets committed.

Build the index (Phase A):

```bash
.venv/bin/python -m src.ingest.build_index
```

Ask one question from the terminal. It prints every step:

```bash
.venv/bin/python -m src.generation.answer "قديش بقدر أغيب عن المحاضرات؟"
```

Open the chat UI:

```bash
.venv/bin/streamlit run app/streamlit_app.py
```

Run the evaluation:

```bash
.venv/bin/python eval/run_eval.py
```

---

## Part 3: The milestones, one at a time

Each milestone follows the same structure: **Why** → **How it works** (with real output from this demo) → **Where in the code** → **Knobs** → **Common mistakes** → **Explaining it to a judge**.

---

### Milestone 1: Load PDFs into clean text
**File:** [`src/ingest/loaders.py`](src/ingest/loaders.py)

**Why.** Everything downstream works on text. If extraction is wrong, every later step is wrong too, and nothing will warn you. Arabic PDFs are notoriously bad at this.

**How it works.** We open each PDF with PyMuPDF and produce one record per page:
```python
{"text": "...", "source": "registration_and_fees.pdf", "page": 2}
```
Keeping the **page number** here is what makes citations like `[registration_and_fees.pdf، ص 2]` possible later.

Three real problems we hit while building this demo, and how the loader handles them:

1. **Broken letters.** The first version of our PDFs extracted `علامة` as `عالمة` and `الامتحان` as `االمتحان`. The cause is the lam-alef ligature (لا): the PDF stores it as one glyph and maps it back to the wrong letters. *Fix:* we generate PDFs with ligatures disabled. With real-world PDFs you can't control this, so always **print the extracted text and read it** before indexing.
2. **Scrambled word order.** PDFs store text in *visual* order. Mixed Arabic + numbers came out as `%15 لا يجوز أن تتجاوز نسبة غياب الطالب`. *Fix:* we take each word with its x-position and re-sort every line right-to-left, which gives `لا يجوز أن تتجاوز نسبة غياب الطالب 15%`.
3. **Tables.** Plain extraction glued cells together (`CPE201هياكل البيانات3`) and lost the headers. *Fix:* PyMuPDF's `find_tables()` locates the table, and we write each row with its headers:
   ```
   رقم المساق: CPE310 | اسم المساق: أنظمة التشغيل | الساعات المعتمدة: 3 | المتطلب السابق: CPE201
   ```
   Now a chunk containing this row still "knows" that 3 means credit hours.

There's also an **OCR fallback**: if a page has almost no text (a scanned image), we render it as an image and run Tesseract on it. Arabic OCR needs the language pack (`brew install tesseract-lang`), which isn't installed right now, so the demo PDFs don't need it.

**Where in the code.** `load_pdf()` is the entry point. `extract_page_text()` handles word order and tables. `table_to_text()` handles tables. `ocr_page()` handles scans.

**Knobs.** `MIN_TEXT_CHARS` (when to treat a page as scanned).

**Common mistakes.** Never looking at the extracted text. Losing page numbers. Flattening tables into number soup.

**Explaining it to a judge.** *"We extract text page by page so every answer can cite its page. Arabic PDFs extract in visual order, so we rebuild each line right-to-left from word positions, and we convert tables into rows that keep their column headers. Scanned pages fall back to OCR."*

---

### Milestone 2: Arabic normalization
**File:** [`src/ingest/normalize.py`](src/ingest/normalize.py)

**Why.** To a computer, `الإنذار` and `الانذار` are different strings, so a keyword search for one misses the other. Arabic has many such variants: hamza forms, ى/ي, ة/ه, diacritics, tatweel (ـ).

**How it works.** `normalize_arabic()` maps all variants to a single form. Real output:
```
الإنذار الأكاديمي          →  الانذار الاكاديمي
مستشفى جـــامعة مَدْرَسَة   →  مستشفي جامعه مدرسه
```
`tokenize()` then splits into words, strips the article "ال" and drops common words that carry no meaning ("في", "من", "ما"...):
```
ما هي نسبة الغياب المسموح بها في المساق؟  →  ['نسبه', 'غياب', 'مسموح', 'بها', 'مساق']
```

**Important design choice.** Normalization is used **only for keyword search (BM25)**, applied to both documents and questions the same way. The original text is kept for display and citations (you don't want to show users "جامعه"), and the embedding model gets the original text because it already understands these variants.

**Knobs.** The `STOPWORDS` list. Whether to map ة→ه (we do, because people type both).

**Common mistakes.** Normalizing documents but not questions, or the other way around. If both sides aren't normalized identically, nothing matches.

**Explaining it to a judge.** *"Arabic has several spellings for the same word. We normalize hamza, alef maqsura, ta marbuta and diacritics on both the documents and the question, but only for keyword search. Users always see the original text."*

---

### Milestone 3: Chunking
**File:** [`src/ingest/chunking.py`](src/ingest/chunking.py)

**Why.** We don't search whole documents, for two reasons:
- **Precision:** a question about fees should retrieve the 3 lines about fees, not a 10-page document that mentions fees once.
- **Cost and focus:** the retrieved text is sent to the LLM. Smaller, relevant pieces mean cheaper calls and fewer distractions for the model.

**How it works.** Our strategy is simple and easy to defend:
1. **Never cross a page**, so every chunk has exactly one page number to cite.
2. **Pack whole lines** until about `CHUNK_SIZE` (600) characters. We never cut mid-line, so a table row is never split.
3. **Overlap:** each chunk starts with the last ~`CHUNK_OVERLAP` (100) characters of the previous one, so a sentence on the boundary appears in both.
4. **Attach metadata** to every chunk: source, page, title, **version**, **date** (from `data/raw/metadata.json`).

Our 7 pages became **11 chunks**. A real chunk from the index:
```
id:      registration_and_fees.pdf#p2#c4
source:  registration_and_fees.pdf     page: 2     version: 2025     date: 2025-08-20
text:    الرسوم الجامعية
         سعر الساعة المعتمدة في كلية الهندسة 45 دينارا أردنيا، وفي باقي الكليات 35 دينارا أردنيا.
         ...
```

**A small trick: contextual headers.** When embedding, `embedding_text()` puts the document title and version on top of the chunk:
`دليل التسجيل والرسوم الجامعية - إصدار 2025` + chunk text. A chunk that only says "الحد الأقصى 18 ساعة" becomes much easier to find once its vector also "knows" which document it's from.

**Knobs.** `CHUNK_SIZE`, `CHUNK_OVERLAP` in `.env`. **Rebuild the index after changing them.**
- Too small (e.g. 150): chunks lose context ("45 دينارا" without saying what for), and answers need many chunks.
- Too big (e.g. 3000): each chunk covers many topics, similarity gets diluted, the LLM receives lots of irrelevant text, and cost goes up.

**Common mistakes.** Cutting in the middle of sentences or table rows. Dropping the page/version metadata. Never trying another chunk size.

**Explaining it to a judge.** *"We chunk by page so each chunk has one citable page, pack whole lines up to 600 characters with 100 characters of overlap, and never split a table row. Every chunk carries file, page, version and date. We picked the size with our eval set: smaller chunks lost context, bigger ones diluted retrieval."*

---

### Milestone 4: Embeddings and the vector store
**Files:** [`src/retrieval/embedder.py`](src/retrieval/embedder.py), [`src/retrieval/store.py`](src/retrieval/store.py)

**Why.** Keyword search fails when the question uses different words from the document ("قديش بقدر أغيب" vs "نسبة الغياب المسموحة"). We need search by **meaning**.

**How it works.** An **embedding model** (`text-embedding-3-large`) turns any text into a vector of 3072 numbers. Texts with similar meaning get vectors pointing in a similar direction. Real output:
```
embed("كم الحد المسموح للغياب؟")  →  shape (3072,)  first numbers [0.0011, 0.0168, -0.0027, -0.0102, 0.0648]
```
"Close in meaning" is measured with **cosine similarity** (from -1 to 1). Real scores for that same question:
```
"لا يجوز أن تتجاوز نسبة غياب الطالب 20% ..."   0.555   ← same topic, different words
"سعر الساعة المعتمدة في كلية الهندسة 45 ..."   0.201
"كيف أطبخ المقلوبة؟"                           0.152
```
The **vector store** keeps one vector per chunk. We normalize every vector to length 1, so the cosine with *all* chunks at once is a single matrix multiplication:
```python
scores = self.vectors @ query_vector      # one score per chunk
```
That's the entire "vector database" in `store.py`. Real projects use FAISS, Chroma, pgvector or Qdrant, which do the same thing with faster approximate search for millions of vectors. For a few thousand chunks, plain NumPy is instant and you can explain every line.

The index is saved to `data/index/` (`embeddings.npy` + `chunks.jsonl`), so we embed once, not on every start.

**Knobs.** `OPENAI_EMBEDDING_MODEL` (`text-embedding-3-small` is cheaper and weaker). Changing the model means rebuilding the index, because vectors from different models aren't comparable.

**Common mistakes.** Embedding the question with a different model than the documents. Forgetting to rebuild after changing chunks. Choosing an English-only embedding model for Arabic.

**Explaining it to a judge.** *"Each chunk becomes a 3072-dimension vector from a multilingual embedding model that handles Arabic well. We embed the question the same way and rank chunks by cosine similarity. At our scale a NumPy matrix product is enough. To scale, we'd swap in a vector DB like pgvector or FAISS without changing the rest of the pipeline."*

---

### Milestone 5: Keyword search (BM25) and hybrid fusion (RRF)
**Files:** [`src/retrieval/bm25.py`](src/retrieval/bm25.py), [`src/retrieval/hybrid.py`](src/retrieval/hybrid.py)

**Why.** Embeddings are great with meaning but fuzzy with **exact tokens**: course codes, symbols, numbers, names. Keyword search is the opposite. Using both covers each one's blind spots.

**How BM25 works.** It scores a chunk higher when it contains the question's words, especially **rare** words (a match on "CPE310" counts far more than a match on "طالب", which is everywhere), and when the chunk is short. It runs on the normalized tokens from milestone 2.

**Real example where hybrid wins.** Question: `رمز W` (what does grade W mean?).
```
Vectors only:  1. study plan p1 (0.169)   2. regulations 2023 p1 (0.162)   3. regulations 2025 p1 (0.154)   ← all wrong
BM25:          1. registration_and_fees.pdf p1 (3.75)                                                     ← correct page
Hybrid:        1. registration_and_fees.pdf p1                                                            ← correct page first
```
The embedding of a one-letter token "W" carries almost no meaning; BM25 matches it exactly.

**How fusion works (RRF).** The two methods score on different scales (cosine 0 to 1, BM25 0 to 20+), so you can't add the scores. **Reciprocal Rank Fusion** uses only each chunk's **rank** in each list:
```
rrf_score(chunk) = 1/(60 + rank_in_vectors) + 1/(60 + rank_in_bm25)
```
Ranked #1 by both → wins. #1 in one list and absent from the other → still scores well. 60 is the standard constant; it stops the very top rank from dominating.

**Where in the code.** `HybridRetriever.retrieve()`: run both searches (15 candidates each), fuse, keep the top 4, and attach all three scores to each chunk so you can see them in the UI.

**Knobs.** `TOP_K` (chunks sent to the LLM), `CANDIDATES`, `RRF_K`. The UI has a toggle to turn BM25 off.

**Honest note from our eval.** On this tiny corpus (11 chunks), BM25 doesn't change the eval scores, because vectors alone already find every gold page. Hybrid matters as documents grow and for exact-token questions like the one above. Saying this honestly to a judge is better than claiming a gain you didn't measure.

**Explaining it to a judge.** *"We run semantic search and BM25 keyword search in parallel and merge them with Reciprocal Rank Fusion, which combines ranks instead of incomparable scores. Vectors catch paraphrases and dialect; BM25 catches exact tokens like course codes and the grade symbol W."*

---

### Milestone 6: Query rewriting (dialect + follow-up questions)
**File:** [`src/generation/rewrite.py`](src/generation/rewrite.py)

**Why.** Two problems break retrieval before it even starts:
1. **Dialect:** students ask `قديش بقدر أغيب؟`, but the documents say `نسبة الغياب المسموحة`. No shared words for BM25, and weaker vectors.
2. **Follow-ups:** in a chat, "وكم ساعة معتمدة إله؟" (how many credits does *it* have?) means nothing on its own. Searching it finds nothing.

**How it works.** One cheap LLM call (`gpt-5-nano`) takes the last few chat turns plus the new question and returns a **standalone search query in formal Arabic**. It's told not to answer and not to add information. Real rewrites from this demo:
```
قديش بقدر أغيب عن المحاضرات؟
  → ما الحد الأقصى للغياب عن المحاضرات في المقرر الدراسي؟

(after asking about شبكات الحاسوب)  وكم ساعة معتمدة إله؟
  → كم عدد الساعات المعتمدة لمساق شبكات الحاسوب CPE320؟
```
We **search** with the rewritten query, but still show the LLM the student's original question too.

**Measured effect** (eval with rewriting turned off, `--no-rewrite`):
```
q10 dialect     "إذا انسحبت من مادة بالأسبوع التاسع شو بصير؟"  → wrong chunks retrieved → refused (should have answered)
q11 follow-up   "وكم ساعة معتمدة إله؟"                       → best cosine 0.178 → refused by the gate
```
Turning rewriting on fixed both. (Full numbers are in milestone 10.)

**Cost.** One extra small LLM call per question (adds ~1 to 2 seconds).

**Common mistakes.** Letting the rewriter answer the question or invent facts. Using the rewritten text as the final answer prompt and losing the student's real wording.

**Explaining it to a judge.** *"Before searching, a small model rewrites the question into standalone formal Arabic using the chat history. That handles Palestinian dialect over formal documents and follow-up questions. Our eval shows both cases fail without it and pass with it."*

---

### Milestone 7: The refusal gate
**File:** [`src/generation/answer.py`](src/generation/answer.py) (look for `refused_by_gate`), threshold in [`config.py`](config.py)

**Why.** Judges *will* ask something outside your documents. The worst outcome is a confident made-up answer. The cheapest way to avoid it: if nothing in the documents is close to the question, don't even ask the LLM.

**How it works.** After retrieval we look at the **best cosine similarity**. If it's below `REFUSAL_THRESHOLD` (0.30), we return the fixed refusal sentence immediately, with no LLM call, so there's nothing that can hallucinate.

**How we chose 0.30** (best cosine for each eval question, with rewriting on):
```
answerable questions:     lowest 0.397   (range 0.40–0.53)
"كيف أطبخ المقلوبة؟"       0.099   → refused by the gate ✔
"من هو رئيس جامعة النخيل؟"  0.441   → passes the gate...
"كم رسوم السكن الجامعي؟"    0.413   → passes the gate...
```
0.30 sits safely below every answerable question. But the last two out-of-scope questions **look** relevant (they mention the university, fees) and score as high as real questions. **No threshold can separate them.** That's why there's a **second layer**: the answer prompt (milestone 8) tells the LLM to refuse when the chunks don't contain the answer. Both questions were correctly refused by that second layer.

**Two layers, two jobs:**
- **Gate:** catches clearly off-topic questions, for free, with zero hallucination risk.
- **Prompt rule:** catches on-topic-sounding questions whose answer simply isn't in the documents.

**Knobs.** `REFUSAL_THRESHOLD`. Too high → you refuse real questions (in our eval, rewriting off pushed a real question down to 0.319). Too low → more off-topic questions reach the LLM (still caught by layer 2, but they cost tokens).

**Explaining it to a judge.** *"Refusal has two layers. If the best match is below a similarity threshold we calibrated on our eval set, we refuse without calling the LLM. Otherwise the prompt forces a fixed refusal sentence when the retrieved text doesn't contain the answer. Our eval has three out-of-scope questions and all are refused."*

---

### Milestone 8: Grounded generation, citations and conflicting versions
**Files:** [`src/generation/prompts.py`](src/generation/prompts.py), [`src/generation/answer.py`](src/generation/answer.py), [`src/generation/llm.py`](src/generation/llm.py)

**Why.** Retrieval found the right text. Now the LLM must turn it into a good answer **without adding anything from its own memory**. That's **grounding**.

**How it works.** We send the LLM:
1. A **system prompt** with five rules: use only the sources; cite every fact as `[file، ص page]`; if it's not there, reply with exactly the refusal sentence; if two versions conflict, trust the newer one and mention the old one; answer in simple formal Arabic.
2. The **numbered sources**, each labeled with file, page, title, version and date:
   ```
   [المصدر 1 | الملف: student_regulations_2025.pdf | ص 1 | نظام الدراسة لمرحلة البكالوريوس - إصدار 2025 (2025-08-15)]
   لا يجوز أن تتجاوز نسبة غياب الطالب 20% ...
   ```
3. The student's original question plus the rewritten one.

The version/date labels are what make **conflict handling** work. Real answer to `قديش بقدر أغيب عن المحاضرات؟`:
```
الحد الأقصى المسموح به للغياب في المقرر هو 20% من مجموع الساعات المقررة للمساق؛ وإذا تجاوز الطالب هذه النسبة
دون عذر مقبول يُحرم من التقدم للامتحان النهائي ويُعتبر راسباً في المساق [student_regulations_2025.pdf، ص 1].

الإشارة: الإصدار الأقدم (2023) كان ينص على حد غياب أقصاه 15% بدل 20% [student_regulations_2023.pdf، ص 1].
```
Both versions were retrieved, and the model picked 2025 because the label says it's newer, then flagged the old value.

`llm.py` also records **tokens** for every call, so you can quote cost per answer (about 1,500 tokens on average in our eval; multiply by your model's price per token).

**Knobs.** `OPENAI_CHAT_MODEL`. The prompt wording itself (the most powerful knob; test changes with the eval). `OPENAI_REASONING_EFFORT` (`low` = faster).

**Common mistakes.** A vague prompt ("be helpful") that lets the model fill gaps from memory. Not labeling sources, which makes citations impossible. Not putting dates on versions, which makes conflicts unresolvable.

**Explaining it to a judge.** *"The LLM only sees the retrieved chunks, each labeled with file, page, version and date. The prompt forces citations and a fixed refusal sentence, and resolves conflicts by trusting the newest version while mentioning the old one. Our LLM judge rated every answer in the eval as faithful to its sources."*

---

### Milestone 9: The chat UI
**File:** [`app/streamlit_app.py`](app/streamlit_app.py)

**Why.** Judges score a live demo, and the bonus points need a usable product with **Arabic RTL** support.

**How it works.** Streamlit turns a Python script into a web page. The script **reruns top to bottom on every interaction**:
- `st.session_state.messages` remembers the chat between reruns (and gives the rewriter its history).
- `@st.cache_resource` loads the index once instead of on every rerun.
- A small CSS block sets `direction: rtl` for Arabic.

Under every answer:
- **📚 المصادر**: the chunks used, with file and page, so the user can verify.
- **🔍 كيف وصلت للإجابة؟**: the rewritten query, best cosine vs threshold, and each chunk's RRF/cosine/BM25 scores. Use this panel to *learn*: watch what each step did.

The sidebar has **toggles** to turn rewriting or BM25 off (compare answers live), **PDF upload** (saves the file and rebuilds the index), and **new chat**.

**Known behavior.** Wait for an answer before sending the next question. Streamlit cancels a running answer if new input arrives, and that answer disappears from the chat.

**Explaining it to a judge.** *"It's a Streamlit chat with RTL Arabic. Each answer shows its sources, and a transparency panel shows the rewritten query and retrieval scores. Admins can upload a new PDF, and the index rebuilds immediately."*

---

### Milestone 10: Evaluation
**Files:** [`eval/questions.jsonl`](eval/questions.jsonl), [`eval/run_eval.py`](eval/run_eval.py)

**Why.** Without measurement, "it seems to work" is a feeling, not a fact. Evaluation tells you whether a change helped, and it's exactly what judges ask for ("how did you measure quality? what did you improve?").

**How it works.** `questions.jsonl` has **14 questions** written with known answers and known source pages: lookups, table questions, version conflicts, dialect, a multi-turn follow-up, and 3 out-of-scope questions. For each one, `run_eval.py` runs the full pipeline and measures:

| Metric | Meaning |
|---|---|
| **Hit@4** | Did at least one of the 4 retrieved chunks come from the correct page? |
| **Precision@4** | What fraction of the 4 retrieved chunks came from a correct page? |
| **Refusal accuracy** | Refused exactly when it should have (out-of-scope) and answered otherwise |
| **Correct** | An LLM judge compares the answer to the reference answer |
| **Faithful** | An LLM judge checks every claim is supported by the retrieved chunks (no hallucination) |
| **Cited** | The answer contains a `[file، ص N]` citation |

**Real results from this demo:**

| Setup | Hit@4 | Precision@4 | Refusal acc. | Correct | Faithful | Cited | Avg time |
|---|---|---|---|---|---|---|---|
| **Full system** | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 5.4 s |
| Without BM25 (`--dense-only`) | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 1.00 | 5.8 s |
| Without rewriting (`--no-rewrite`) | 0.91 | 0.48 | 0.86 | 0.82 | 0.91 | 0.82 | 3.0 s |

How to read it:
- **Rewriting earns its cost:** without it, the dialect and follow-up questions fail. It costs ~2.4 s per question.
- **Precision@4 = 0.50** is expected here: with only 11 chunks, often just 1–2 chunks are on the right page, and the other 2–3 slots get filled with neighbours. Hit@4 is the more important number for us (did the right page arrive at all).
- **BM25 shows no gain on this tiny set** (see milestone 5 for where it does help).
- The full per-question details, including the judge's reason for each verdict, are saved in `eval/results/*.json`.

**Knobs.** Add questions! 14 is a minimum. Every bug you find in the UI should become an eval question.

**Common mistakes.** Writing the eval questions *after* tuning (you'll unconsciously pick ones that pass). Only testing questions that have answers (never testing refusal). Changing several things at once, so you can't tell which one helped.

**Explaining it to a judge.** *"We have a 14-question test set with reference answers and source pages, covering dialect, tables, conflicts, follow-ups and out-of-scope. We measure Hit@k, Precision@k, refusal accuracy, and correctness and faithfulness with an LLM judge. Turning off query rewriting dropped correctness from 100% to 82%, which is why we kept it."*

---

## Part 4: Experiments to try
Change one thing, rerun the eval, compare. This is the loop that real RAG work is made of.

1. **Turn off rewriting or BM25** in the UI sidebar, then ask the same dialect question. Compare the "كيف وصلت للإجابة" panels.
2. **Tiny chunks:** set `CHUNK_SIZE=150` and `CHUNK_OVERLAP=30` in `.env`, rebuild the index, rerun the eval. Watch the chunk count, Hit@4 and answers that lose context.
3. **Huge chunks:** `CHUNK_SIZE=3000`, rebuild. Every page becomes one chunk. What happens to Precision@4 and tokens?
4. **Threshold too high:** `REFUSAL_THRESHOLD=0.45`, then rerun the eval. Which real questions get refused now?
5. **Fewer chunks:** `TOP_K=1`. Does the conflict question still mention both versions?
6. **Break the prompt:** in `prompts.py`, delete rule 3 (the refusal rule), then ask "من هو رئيس جامعة النخيل؟". Does it make something up?
7. **Add a document:** upload any PDF in the sidebar and ask about it.
8. **Write 3 new eval questions** of your own, including one that you expect to fail, and see if it does.

Restore `.env` values afterwards and rebuild the index.

---

## Part 5: Glossary
| Term | Meaning |
|---|---|
| **RAG** | Retrieval-Augmented Generation: retrieve relevant text first, then have an LLM answer from it |
| **LLM** | Large Language Model (e.g. GPT): generates text |
| **Hallucination** | A fluent, confident answer that isn't true or isn't supported by the sources |
| **Grounding** | Forcing answers to come only from provided sources |
| **Chunk** | A small piece of a document, the unit we search and cite |
| **Metadata** | Labels on a chunk: file, page, version, date |
| **Embedding** | A vector (list of numbers) representing the meaning of a text |
| **Vector store** | Where chunk vectors are kept and searched (here: NumPy; in production: FAISS, Chroma, pgvector...) |
| **Cosine similarity** | How close two vectors point (1 = same direction/meaning, 0 = unrelated) |
| **Dense retrieval** | Search by embedding similarity (meaning) |
| **BM25** | Classic keyword ranking: rewards rare shared words, short chunks |
| **Sparse retrieval** | Keyword-based search like BM25 |
| **Hybrid search** | Dense + sparse together |
| **RRF** | Reciprocal Rank Fusion: merges ranked lists using ranks, not scores |
| **Top-k** | How many retrieved chunks we keep and send to the LLM |
| **Reranking** | A second, more accurate model re-orders the top candidates (not in this demo; a common next step) |
| **Query rewriting** | Turning the user's question into a better search query (dialect → formal, follow-up → standalone) |
| **Normalization** | Mapping spelling variants to one form so keyword search matches |
| **OCR** | Optical Character Recognition: reading text from images/scans |
| **Refusal** | Saying "not in my documents" instead of guessing |
| **Hit@k** | Did the right source appear in the top k? |
| **Precision@k** | What fraction of the top k are right? |
| **Faithfulness** | Is every claim in the answer supported by the retrieved text? |
| **LLM-as-judge** | Using an LLM to grade answers against a reference |
| **Token** | The unit LLMs read and bill by (roughly a word piece) |

---

## AI disclosure
This demo was written by **Claude Code (Claude Opus 5.5)** at the request of Team Checkmate, as learning material before the IEEE RAG Hackathon: all code, the fictional sample documents, the eval questions and this README. The examples and numbers in this README are real outputs from running the demo. Libraries used: OpenAI Python SDK, PyMuPDF, rank-bm25, NumPy, Streamlit, python-dotenv, pytesseract, Pillow. No code was copied from other projects.
