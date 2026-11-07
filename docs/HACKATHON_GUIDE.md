# Hackathon Reference Guide — IEEE RAG Hackathon (Bethlehem University)

> English digest of `IEEE_RAG_Hackathon_Judging_Guide_AR.pdf` (judging guide v1.0, BinX Tech + IEEE Bethlehem University Student Branch), plus Team Checkmate's playbook.
> Organizers may change rules before the day and must announce them. Announcements win over this file; update it when they happen.
> Claude's working rules live in `/CLAUDE.md`. This file is reference material to read when a task needs it.

---

## 1. The event in one paragraph
Each team gets a real problem (picked or assigned by lottery from the 10 below). The team builds a **RAG system** that answers user questions **grounded in trusted sources**, then pitches it as a **product with commercial viability**. Build window: **10:30 AM to 3:00 PM**, which is **4.5 hours**. Submit **before 3:00 PM**. Judging runs 3:00 to 4:30 PM.

AI tools (including Claude) are **allowed and encouraged**, as long as the README says so. Judges test whether the team **understands** what was built in Q&A.

## 2. Scoring: 100 points + up to 10 bonus (max 110)

| # | Criterion | Pts | Sub-items |
|---|-----------|-----|-----------|
| 1 | **RAG technical quality** | **30** | Data prep & ingestion 5 · Retrieval 10 · Generation & grounding 10 · Evaluation 5 |
| 2 | Problem understanding & fit | 15 | Problem clarity & size 5 · Why RAG 5 · User & local context fit 5 |
| 3 | Code & engineering | 15 | Structure 5 · Runnability & docs 5 · Security, privacy & scalability 5 |
| 4 | Business plan & numbers | 15 | Market (TAM/SAM/SOM) 5 · Revenue model & pricing 5 · Costs & financial projections 5 |
| 5 | Marketing plan | 10 | Audience & positioning 3 · Channels & launch 4 · KPIs & 90-day timeline 3 |
| 6 | Presentation & communication | 10 | Structure & story 4 · Live demo 3 · Q&A & teamwork 3 |
| 7 | Innovation | 5 | Something unusual: dialect handling, multi-agent, auto-eval loop, image/voice |

Split: 60 points technical (RAG 30 + problem 15 + code 15), 35 business side (business plan 15 + marketing 10 + presentation 10), 5 innovation. Business is about a third of the score, so it can't be skipped.

### What judges look for in each sub-item
- **Data prep (5):** document cleaning, a **chunking strategy you can justify**, metadata kept (source, **page number**), and handling of PDFs, **tables and Arabic text**.
- **Retrieval (10):** embedding model and vector store that fit the data, tuned **Top-k**, **hybrid search** or **reranking** or metadata filtering. *What counts most is the quality of the retrieved chunks, not how many techniques you used.*
- **Generation & grounding (10):** answers built **only from sources**, **citations**, **clear refusal when the info isn't there** instead of hallucinating, a solid prompt, clean language.
- **Evaluation (5):** a test set of **at least 10 questions with reference answers**, metrics such as **Precision@k** and **Faithfulness**, analysis of system errors, and **what you improved because of it**. *(This is tie-break #2.)*
- **Problem clarity (5):** who is affected, how big the pain is, a number or evidence, said simply.
- **Why RAG (5):** why not a plain LLM or keyword search, and what value only RAG adds.
- **User/local fit (5):** Arabic and dialect, ease of use, privacy, **internet limits and cost**.
- **Code structure (5):** clear layers (ingestion / retrieval / generation / UI), clear names, maintainable.
- **Runnability (5):** README with install, run, architecture, requirements file, **sample data**. **A judge must be able to run it without our help.**
- **Security/scalability (5):** API keys in **env vars**, protection of sensitive data, a clear scaling story (more docs, more users, cost estimate).
- **Market (5):** TAM/SAM/SOM with **sourced** numbers, a precise target customer.
- **Revenue (5):** who pays and why, pricing rationale, unit economics (**CAC, LTV, margin**), with assumptions stated.
- **Costs/projections (5):** running costs (API, hosting, team), **12 to 36 month** revenue projections, **break-even point**, assumptions stated.
- **Audience/positioning (3):** a specific **persona**, a clear message, what sets us apart from alternatives.
- **Channels/launch (4):** realistic acquisition channels, possible partnerships, rough budget, phased launch.
- **KPIs/timeline (3):** numeric KPIs (users, conversion, retention) and a **first-90-days** plan.
- **Story (4):** problem, solution, market, marketing, ask. Clear slides, **on time**.
- **Live demo (3):** a working system on real questions, showing the answer **with its source**. A recorded video is fine as a substitute. **No demo and no video means 0.**
- **Q&A & teamwork (3):** deep understanding even if AI wrote code, clear role split.

### How a sub-item is scored (level × weight)
| Level | % of item |
|---|---|
| Excellent: solid, evidenced, beyond expectations | 90–100% |
| Very good: correct, complete, minor notes | 75–89% |
| Good: does the job, clear gaps | 60–74% |
| Acceptable: partial or shallow | 40–59% |
| Weak: incomplete or unconvincing | <40% |
| Missing: not provided or not verifiable | 0% |

### Bonus (+10, outside the 100)
| Item | Pts | Requirement |
|---|---|---|
| Working full product | up to 5 | Web app, mobile app or UI over an API, deployed via link or runnable in front of judges |
| UX & design | up to 2 | Clear, smooth, consistent UI that **supports Arabic and RTL** |
| Productivity features | up to 3 | Login, admin dashboard, **upload new docs**, saved chat history, analytics dashboard |

**Bonus only counts if we score at least 15/30 on RAG technical quality.** A nice UI with no real retrieval behind it earns no bonus.

### Penalties
| Violation | Effect |
|---|---|
| Fabricated numbers or sources in business plan | −3 to −5 from Business |
| **API keys or sensitive data exposed in code** | −2 from Security |
| Copying a project or ready code **without attribution** | up to −10 or **disqualification** |
| Late submission | −2 per 5 min late, max −10 |
| Going over presentation time | Warning, then presentation stopped |

### Tie-breaks
1. Higher RAG technical score. 2. Higher **Evaluation** sub-item. 3. One extra committee question to both teams.

---

## 3. Deliverables (checklist, all before 3:00 PM)
- [ ] **Code**: GitHub link or zip. Must contain **README**, **requirements file**, **`.env.example`**, **sample data**.
- [ ] **Presentation**: PDF or PPTX, **max 12 slides**, covering the 9 required slides below.
- [ ] **Video (optional but strongly recommended)**: 2–3 min screen recording of the system working. Preferably **3 real questions**, including **one answered with a source** and **one out-of-scope that gets refused**. This also counts as a backup for the live demo.
- [ ] **AI disclosure**: a short paragraph in README listing the AI tools used and what they produced.

### Required slide content (9 slides; the scoring criterion each one feeds)
| # | Slide | Content | Criterion |
|---|---|---|---|
| 1 | Problem & evidence | Problem, who's affected, a stat proving its size | 2 |
| 2 | Solution & RAG architecture | Simple diagram: data → retrieval → generation → UI | 1 |
| 3 | Demo | Screenshots or video link, example Q&A **with sources** | 6 |
| 4 | Market | TAM/SAM/SOM **with sources** | 4 |
| 5 | Revenue & pricing | Who pays, how much, unit economics | 4 |
| 6 | Costs & projections | Running cost, 12–36 month projections, break-even | 4 |
| 7 | Marketing | Audience, channels, rough budget, KPIs, 90-day plan | 5 |
| 8 | Competitors & differentiation | Current alternatives, why we're better or different | 7 |
| 9 | Team & next steps | Member roles, what we'll do after the hackathon | 6 |

**Every number and stat in the business plan must cite its source.** Our own estimates are OK if labeled as **assumptions**. Made-up numbers lose points.

---

## 4. Judging session (3:00–4:30 PM)
- **10 minutes per team: 5 min pitch + 4 min Q&A + 1 min changeover.** Five minutes for 9 slides plus a demo is tight, so rehearse with a timer.
- Each committee has a **technical judge** and a **business/marketing judge** (often a third from industry). Each scores independently, and the final score is the average.
- **Surprise test:** judges prepare **3 test questions per problem, including one out-of-scope**, and type them **directly into our system**. This checks retrieval and grounding for real. Our system must:
  1. answer in-scope questions correctly **with citations (doc + page)**;
  2. **refuse** out-of-scope questions cleanly ("not found in the provided sources"), never hallucinate;
  3. be fast and stable on a fresh question we've never seen.

### Possible hidden technical challenges (organizers may announce or spring these)
- **Dialect questions** (e.g. Palestinian Arabic) over documents written in **Modern Standard Arabic**.
- **Scanned PDFs** or PDFs full of **tables**.
- **Conflicting sources**: an old version and a new version of the same document.
- **Out-of-scope questions** to test refusal.
- **Multi-turn conversations** that depend on earlier context.

**Design for all five from the start.** They are cheap to handle if planned in, and each one is a demo moment.

### Judges' question bank: every team member must be able to answer these without notes
1. Why did you choose this chunking strategy? What happens if you change chunk size or overlap?
2. Which embedding model did you use and why? How does it handle Arabic?
3. What does the system do when asked about something not in the documents? (live test)
4. How did you measure quality? What's the worst question it fails on, and why?
5. How does it handle conflicting or outdated information?
6. What does one answer cost? How does that change at 10,000 users?
7. Where did your market numbers come from? What's the weakest assumption in your financial plan?
8. What did you write yourselves vs what did AI generate? Explain this part of the code.
9. How do you protect the privacy of sensitive data in the system?
10. Who are the first three customers you'll contact after the hackathon, and what will you tell them?

---

## 5. The 10 candidate problems
Organizers ideally prepare 5–10 documents per problem.

| # | Problem | Domain | Difficulty | Users | Data | RAG challenge | Bonus idea |
|---|---|---|---|---|---|---|---|
| 1 | Smart academic advisor | Education | Easy | University students & advisors | Student guide, university regulations, study plans (PDF) | Exact answers with course codes, handling tables & prerequisites | Web app or WhatsApp bot + dashboard of most-repeated questions |
| 2 | Legal & procedural assistant | Law/services | Medium | Citizens, small business owners | Published laws (e.g. **Al-Muqtafi** system), procedure guides | Cite the exact article, tell the latest version from amendments, warn that it's not legal advice | Platform that saves questions + generates a personal procedure checklist |
| 3 | Farmer's assistant | Agriculture | Medium | Farmers, agri-extension workers | Extension bulletins, open FAO guides | **Dialect questions over MSA docs** ("ليش ورق الزيتون بصفر؟"), agricultural terms | Mobile app or **voice bot** answering in the farmer's dialect |
| 4 | Safe primary health guidance | Health | Advanced | Patients, families, elderly | Official drug leaflets, open WHO guidance | Safety first: no diagnosis, flag emergencies, refuse out-of-scope, cite every answer | Interface that explains drug leaflets simply, voice mode for the elderly |
| 5 | Customer support assistant for a software company | Business | Easy | Support team & customers | Open-source product docs + team-written sample tickets | Step-by-step answers with links, detect intent, **escalate to a human when unsure** | Embeddable chat widget + support info dashboard |
| 6 | Internal company knowledge | HR | Medium | Employees, HR management | Sample HR policies (team-made or from public regs) | **Access control (each employee sees only what they're allowed to)**, policy versioning | User accounts with **RBAC** + admin doc-upload dashboard |
| 7 | Contract analyzer | Law/business | Advanced | SMB owners, freelancers | Open contract templates (employment, services, lease) | Extract obligations, durations, penalties, compare clauses to a reference template, cite the page | Upload a PDF contract → downloadable risk report |
| 8 | Tourism & heritage guide | Tourism | Easy | Tourists, guides, municipalities | Historical texts, open tourist guides, Ministry of Tourism material | Multilingual, multiple names for the same site, full-day route planning | Mobile app with map + custom visit schedule |
| 9 | Grants & funding assistant | Entrepreneurship | Medium | Entrepreneurs, NGOs | Public grant announcements & applicant guides | Match an org profile to eligibility criteria, extract deadlines, summarize requirements | Personalized opportunities dashboard + deadline alerts |
| 10 | Cybersecurity & compliance assistant | Tech | Advanced | SMBs, IT teams | Open **NIST CSF** docs, general standard summaries, sample policies | Map policy clauses to reference controls, find gaps, suggest prioritized improvements | Interactive, exportable gap report |

### Picking strategy (if we get to choose)
Choose for the **highest total score**, not the coolest idea:
- **Clear B2B buyer**: makes revenue, pricing and TAM/SAM/SOM easy to defend (#5, #6, #10, #7, #9).
- **Strong "why RAG" + local fit**: Arabic, Palestinian context, citations matter (#2, #3, #6, #1).
- **Natural bonus features**: #6 (RBAC + upload dashboard) maps almost 1:1 to the productivity bonus. #1, #5, #9 have dashboards built in.
- **Avoid over-scoping advanced problems** (#4, #7, #10) unless we're confident we can hit grounding and safety in 4.5h.
- If it's a **lottery**, the generic pipeline below handles any of them. Just swap in the domain prompt, data and pitch.

---

## 6. Technical playbook (how we build it)

### Architecture (keep the layers separate; it's graded)
```
data/            raw sample docs (committed, small) + processed/
src/ingest/      loaders (PDF, OCR fallback, tables), Arabic normalization, chunking, metadata
src/retrieval/   embeddings, vector store, BM25, hybrid fusion, reranker, filters
src/generation/  prompts, query rewriting (dialect→MSA, multi-turn condensation), grounded answer + citations, refusal
src/api/         thin API (FastAPI or similar)
app/             UI (Arabic, RTL)
eval/            questions.jsonl (≥10, gold answers + gold source), run_eval.py, results/
.env.example     every key the app reads, with no real values
README.md        install · run · architecture diagram · eval results · AI disclosure · attribution
```

### Pipeline decisions (each must be explainable in Q&A)
- **Arabic normalization** for both indexing and queries: strip diacritics (tashkeel) and tatweel, unify alef forms (أ إ آ → ا), ى→ي, optionally ة→ه for the BM25 side only. Keep the original text for display and citation.
- **Chunking:** structure-aware first (headings, articles, numbered clauses, table rows), with a size and overlap fallback. Every chunk carries `source`, `page`, `section`, and `version/date`. Keep tables whole or convert them to row-level text with headers.
- **PDFs:** text layer first; **OCR fallback** for scanned pages (Tesseract `ara`, or a vision LLM). Detect empty text layers automatically.
- **Embeddings:** a **multilingual model that's strong on Arabic** (e.g. `BAAI/bge-m3` or `intfloat/multilingual-e5-large`). **Download weights the night before.** Venue internet may be bad.
- **Retrieval:** **hybrid = dense + BM25**, fused with RRF, then a **reranker** (e.g. `BAAI/bge-reranker-v2-m3`) on the top ~20, keeping the top ~5. Tune k with the eval set. Add metadata filters (version, doc type, user role).
- **Query rewriting:** LLM rewrites **dialect → MSA** and condenses **multi-turn** history into a standalone question before retrieval. Show this in the demo, since it covers both innovation and the hidden challenges.
- **Conflicting versions:** prefer the newest `version/date`. When sources disagree, say so and cite both.
- **Grounded generation:** the system prompt forces answers **only from the provided context**, with **inline citations `[doc, p.N]`** and an explicit refusal ("لم أجد هذه المعلومة في المصادر المتاحة") when context is insufficient. Add a **retrieval-score threshold** so out-of-scope questions get refused *before* the LLM is called. Answer in the user's language/dialect level. Domain disclaimers where needed (legal and health).
- **LLM:** use the strongest model we can afford for answers (e.g. `claude-sonnet-5-5`) and a cheaper one for rewriting/judging (e.g. `claude-haiku-5-5`). Keys only via `.env`. Track tokens per answer so we can quote **cost per answer** and **cost at 10,000 users**.

### Evaluation (5 pts + tie-break #2, so take it seriously)
- Write **12–15 questions in the first 30 minutes**, before the pipeline exists. Include: easy lookups, table questions, **≥2 dialect questions**, **≥2 out-of-scope**, 1 conflicting-version question, 1 multi-turn follow-up. Each gets a gold answer + gold source/page.
- Metrics: **Precision@k / Recall@k** (did the gold chunk come back?), **Faithfulness** (LLM-as-judge: is every claim supported by the cited context?), **refusal accuracy** on out-of-scope, latency, cost.
- Keep a **before → after table** (e.g. "dense-only P@5 0.55 → hybrid+rerank 0.80") and **one failure case analysis**. This goes in the README and on a slide. Judges explicitly ask for "what you improved because of it".
- `python eval/run_eval.py` should regenerate results in one command.

### Engineering hygiene (cheap points, and avoids penalties)
- `.env` in `.gitignore` from minute one. **Never commit a key.** Scan before every push (`git grep -nE "sk-|api_key\s*=\s*['\"]"`).
- `requirements.txt` with pinned versions. Small **sample data** committed so the judge can run it.
- **Test a fresh clone** on another teammate's laptop before submitting: the README steps must work as written.
- Pre-built **index cached to disk** so the demo doesn't re-embed everything.
- Attribute every external code source or template in README. If we prepare boilerplate before the event, **disclose it**.

---

## 7. Timeline for the day (270 min)
| Time | What |
|---|---|
| 10:30–10:50 | Pick/receive problem, read docs, assign roles, **write eval questions**, sketch architecture |
| 10:50–12:15 | **Baseline end-to-end** (ingest → hybrid retrieve → grounded answer with citations) in parallel with UI shell and market research |
| 12:15–13:15 | Run eval → fix worst failures (rerank, chunking, dialect rewrite, refusal threshold). Bonus features (upload, history, dashboard) |
| 13:15–14:00 | **Feature freeze.** Slides (≤12), README (incl. eval table + AI disclosure), record the 2–3 min video |
| 14:00–14:30 | Fresh-clone test, key scan, rehearse 5-min pitch twice with a timer, drill the 10 judge questions |
| **14:30–14:45** | **Submit.** 15-min buffer. Late = −2 per 5 min |

### Suggested roles (adjust to strengths)
- **RAG/backend owner**: ingestion, retrieval, generation, eval.
- **Product/frontend owner**: Arabic RTL UI, bonus features, demo video, deploy.
- **Business/pitch owner**: market sizing with sources, pricing and unit economics, costs and break-even, marketing plan, deck, pitch lead.
Everyone must be able to explain the architecture and answer judge questions 1–10.
