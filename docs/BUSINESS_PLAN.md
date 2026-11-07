# المرشد الذكي (Smart Academic Advisor): Business Plan

Team Checkmate · IEEE RAG Hackathon · Nov 7 2026
Owner: Aboud Fialah. This is the source of truth for the deck and for Q&A.

**Rule:** every number is either **[S]** sourced (link in the table at the end) or **[A]** our own assumption.
🔴 = survey placeholder. It gets replaced with real results when the form closes. **Never present a 🔴 value.**

---

## 1. Problem and user
- **User:** Birzeit University undergraduates. About **14,000 students** [S1].
- **Pain** (as proposed by the hackathon hosts):
  - **Prerequisites:** "Can I take this course next semester?"
  - **Study plan:** "What's left for me to graduate?"
  - **Regulations:** withdrawal, academic probation, transferring majors.
- **Why it hurts:** the answers are spread across long Arabic PDFs (student guide, regulations, study plans) full of tables and articles. The alternatives are waiting for a busy advisor or asking WhatsApp groups that are often wrong. One wrong answer can mean a missed prerequisite, a delayed graduation, or probation.
- **Evidence:**
  - 14,000 students [S1].
  - Quick survey of Birzeit IT-faculty students (Nov 7 2026, 8 questions, anonymous):
    - 🔴 XX% registered without knowing a prerequisite (Q2)
    - 🔴 XX% need more than an hour to find a reliable answer (Q4)
    - 🔴 XX% acted on wrong information from friends or groups (Q6)
    - 🔴 XX% would definitely use the assistant (Q7)
    - Sample: 🔴 N students. Limitation: IT faculty only, so say so on the slide.
  - Backup: in the US, the median caseload is **296 students per full-time advisor** [S2] (US data, 2011, not local).

## 2. Solution and why RAG
A web assistant that answers in Arabic, including Palestinian dialect, **only** from Birzeit's official documents. Every answer cites `[document, page]`, and the assistant **refuses** when the documents don't cover the question.

| Why not... | Our answer |
|---|---|
| **ChatGPT?** | It doesn't know Birzeit's regulations or study plans, so it guesses and can be confidently wrong about a prerequisite. We answer only from official documents, cite the page, and refuse when the answer isn't there. |
| **Ctrl+F on the PDF?** | Students ask in dialect ("قديش لازم معدلي عشان ما آخذ إنذار؟"), while the regulations use formal Arabic with different words. We rewrite dialect into formal Arabic and search by meaning plus keywords (hybrid). |
| **Just ask the advisor?** | One advisor serves many students and is busiest at registration. We're available 24/7 for the repeated questions, so advisors can focus on the hard cases. **We support advisors; we don't replace them.** |

## 3. Business model: who pays
**B2B.** The **university administration pays a yearly license** (Deanship of Student Affairs / Registrar). **Students use it for free.**
Pitch line: *"Free for every student, sustainable through the university."*

## 4. Market (TAM / SAM / SOM)
Customers are **institutions**. Students are their users, and the number of students sets the price tier.

| | Customers (who pays) | Users | Source |
|---|---|---|---|
| **TAM** | Universities in the Arab world | ~15M tertiary students | [S3] (news report on a Nov 2026 UNESCO report; verify against the report itself) |
| **SAM** | ~51 higher-education institutions in Palestine | 214,081 students (2021/22, the last full West Bank + Gaza figure; Gaza data stopped after Oct 2023) | [S4], [S5] |
| **SOM** (3 years) | **9 institutions:** Birzeit, Bethlehem, An-Najah + 6 university or community colleges | ~51,000 students (~24% of SAM) | Universities [S1][S6][S7]; which ones sign, and the colleges' size (~1,500 each) [A] |

Expansion story: **Birzeit → 2 more Palestinian universities + colleges (SOM) → all of Palestine (SAM) → the Arab world (TAM).** Jordan (~400k students [S8]) is the natural next market.

## 5. Pricing (Palestine-adjusted) [A]
| Tier | Example | Price per year |
|---|---|---|
| Small, under 5k students | Bethlehem (3,226 [S7]), colleges | **$1,200** ($100/month) |
| Medium, 5–15k | Birzeit (~14,000 [S1]) | **$3,000** ($250/month) |
| Large, over 15k | An-Najah (~25,000 [S6]) | **$5,000** (~$420/month) |

- **Setup fee:** $500 one-time (loading documents and configuration). **Free for Birzeit**, plus **one free pilot semester**.
- Works out to about **$0.20 per student per year**.
- **Comparison:** Ocelot (US) starts at about **$15,000 per feature per year**, and prices by student population [S9][S10].

## 6. Unit economics [A unless marked]
**Cost per answer ≈ $0.004:**
- Answer model gpt-5.4-mini: ~3,000 input + ~300 output tokens × $0.75 / $4.50 per 1M = $0.0036
- Rewrite model gpt-5-nano: ~500 input + ~100 output tokens × $0.05 / $0.40 per 1M ≈ $0.00007
- Query embedding with text-embedding-3-large ($0.13 per 1M): negligible
- Prices [S11] come from third-party aggregators. Check them on OpenAI's pricing page, and replace the token counts with the real cost from `eval/run_eval.py`.

**Cost per student:**
- Usage assumption: 50% of students are active, and each active student asks ~40 questions a year.
- That's **$0.08 per enrolled student per year** ($0.16 per active student).
- At 10,000 students that's ≈ **$800 a year** in API costs.

**Cost and margin per customer** (hosting of ~$600/year charged in full to each customer, which is conservative):

| University | Cost/year | Price | Margin |
|---|---|---|---|
| Bethlehem | ~$860 | $1,200 | ~28% |
| Birzeit | ~$1,720 | $3,000 | ~43% |
| An-Najah | ~$2,600 | $5,000 | ~48% |

**CAC and LTV** (Birzeit as the example):
- **CAC** ≈ $300 (meetings, travel, demos) + $860 (free pilot semester, half a year's cost) = **~$1,160**
- **LTV** = $3,000 × 43% × 3-year lifetime = **~$3,870**
- **LTV/CAC ≈ 3.3×**. The common SaaS rule of thumb is 3× or more.
- **Weakest assumption:** the 3-year customer lifetime, since we have no retention data yet. Margins on small customers are thin; our answer is caching repeated questions and falling API prices (not yet measured).

## 7. Costs, projections and break-even [A]
**Strategy:** start as a bootstrapped student team (founders unpaid in years 1–2), then grow to more institutions so we can pay ourselves in year 3.

| | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| New customers | Birzeit (pilot first semester) | + Bethlehem + 2 colleges | + An-Najah + 4 colleges |
| Total customers | 1 | 4 | 9 |
| Students covered | ~14k | ~20k | ~51k |
| **Revenue** | **$2,000** | **$8,100** | **$18,900** |
| API ($0.08 per student) | $1,100 | $1,600 | $4,100 |
| Hosting (shared) | $600 | $1,200 | $1,800 |
| Marketing + travel | $1,000 | $2,000 | $3,000 |
| **Profit before salaries** | **−$700** | **+$3,300** | **+$10,000** |
| Founder pay (part-time) | $0 | $0 | $9,000 |
| **Net** | **−$700** | **+$3,300** | **+$1,000** |

How the revenue adds up:
- **Year 1:** Birzeit $3,000 × 8/12. The pilot semester is free.
- **Year 2:** $3,000 + Bethlehem ($1,200 + $500 setup) + 2 colleges × ($1,200 + $500).
- **Year 3:** the year-2 licenses ($6,600) + An-Najah ($5,000 + $500) + 4 colleges × $1,700.

**Break-even:**
- **Operating** (excluding salaries): during **year 2** (cumulative turns positive around month 15).
- **Including founder pay:** **year 3**.

Pitch line: *"Bootstrapped in year 1, self-funding in year 2, paying ourselves in year 3."*

## 8. Marketing
### 8a. Personas (illustrative)
- **Buyer: "Dr. Samer"**, Dean of Student Affairs or Director of Admissions & Registration.
  - **Pain:** advisors swamped at registration; the same questions every semester; registration mistakes lead to probation and late graduation.
  - **Wants:** fewer repeated questions, fewer mistakes, data on what students ask.
  - **Says yes if:** it's cheap, built on official documents only, and doesn't replace advisors.
  - **Fears:** wrong answers that hurt the university's credibility; student data privacy.
  - **Message:** *"Cut repeated questions and registration mistakes, built only on your official documents."*
- **User: "Lina"**, 19, second-year CS student at Birzeit.
  - **Pain:** doesn't know if she can skip a prerequisite, or what withdrawing does to her GPA.
  - **Today:** asks WhatsApp groups and gets mixed answers, or waits for her advisor.
  - **Message:** *"Ask in your own words, get a reliable answer from Birzeit's regulations, with the page number."*

### 8b. Channels and launch
- **Buyer (direct sales):**
  - Live demo to the Dean and Registrar (we're Birzeit students).
  - A faculty champion at the IT faculty.
  - The hackathon result and the IEEE network for credibility. Bethlehem University is hosting the hackathon, so we have a first contact there.
- **Users:**
  - Student council and the IEEE student branch.
  - QR posters at registration.
  - Facebook and Instagram: 2.3M active social media user identities in Palestine [S12].
  - A link on Ritaj, if the administration agrees.
  - WhatsApp, depending on survey Q8.
- **Phased launch:**
  1. Semester 1: free pilot at Birzeit's IT faculty
  2. Semester 2: all of Birzeit, paid license starts
  3. Year 2: Bethlehem + 2 colleges
  4. Year 3: An-Najah + 4 colleges

**Year-1 marketing budget: $1,000** [A]

| Item | Amount |
|---|---|
| Social media ads at registration time | $700 |
| Travel and meetings | $100 |
| Posters and QR codes | $100 |
| Demo events | $100 |

### 8c. KPIs (90-day targets) [A]
| Type | KPI | Target |
|---|---|---|
| Users | Students who used it during the pilot | 500 |
| Retention | Return within a month | 40% |
| Satisfaction | Answers rated 👍 | ≥ 80% |
| Quality | Answers with a correct citation (eval) | ≥ 90% |
| Safety | Out-of-scope questions refused | 100% |
| Business | Pilot → paid license | 1 contract (Birzeit) |
| Pipeline | Meetings with new universities | 2 |

The app's analytics dashboard already tracks usage and 👍/👎.

### 90-day plan
| Days | Actions |
|---|---|
| 1–30 | Meet the Dean of Student Affairs and the Registrar · get the official, up-to-date documents · privacy review · launch in the IT faculty with the IEEE branch and the student council |
| 31–60 | Pilot runs · weekly fixes from the eval and feedback · ads at registration · gather advisor feedback |
| 61–90 | Pilot report for the administration (usage, top questions, satisfaction) · sign the paid license · first meeting at Bethlehem |

## 9. Competitors and differentiation
| Alternative | Strength | Weakness |
|---|---|---|
| Academic advisor | Human expert | Busy, office hours only |
| WhatsApp groups and friends | Fast, always available | Often wrong, no source |
| PDFs, student guide, Ritaj | Official and correct | Long, formal Arabic, tables, hard to search |
| ChatGPT and general AI | Fast, understands dialect | Doesn't know Birzeit's regulations, can make things up |
| Ocelot, Mainstay (global) | Mature products | Built for US institutions; Ocelot starts at ~$15k per feature per year [S9] |

**Our edge:**
1. Birzeit's official documents only, with the page cited
2. Refuses instead of inventing
3. Understands Palestinian dialect
4. Priced for Palestine
5. Privacy: no student records needed
6. Supports advisors instead of replacing them

**One line:** *"As accurate as the regulations, as fast as WhatsApp, and in your own dialect."*
Survey Q3 (🔴) will show which alternative students use most.

## 10. Team and next steps
| Name | Role |
|---|---|
| Aboud Fialah | Business plan, marketing, pitch |
| Fadi Bassous | User interface (Arabic RTL app) |
| Adnan Odeh | Data (document prep, extraction, ingestion) |

**First 3 customers:**
- **Birzeit:** our university; pilot first.
- **Bethlehem University:** met today; it's hosting the hackathon.
- **An-Najah:** ~25k students [S6], one of the largest in Palestine.

---

## Sources
| ID | What | Link |
|---|---|---|
| S1 | Birzeit ~14,000 students, 2023/24 | https://www.birzeit.edu/en/node/57453 |
| S2 | NACADA: median 296 advisees per advisor (2011 survey) | https://nacada.ksu.edu/Resources/Clearinghouse/View-Articles/Advisor-Load.aspx |
| S3 | Arab higher education nears 15M students (UNESCO report, news coverage) | https://devdiscourse.com/article/education/4001465-arab-higher-education-nears-15-million-students-unesco-flags-quality-and-jobs-gaps |
| S4 | PCBS: 214,081 higher-ed students in Palestine, 2021/22 | https://pcbs.gov.ps/Portals/_Rainbow/Documents/Education2021_E.html |
| S5 | 51 higher-education institutions in Palestine | https://sdf-pal.org/?p=35989 |
| S6 | An-Najah ~25,000 students (Times Higher Education) | https://timeshighereducation.com/node/624453 |
| S7 | Bethlehem University 3,226 students, fall 2023 | https://www.bethlehem.edu/?p=10618 |
| S8 | Jordan ~400,000 university students (minister, Jan 2024) | https://jordantimes.com/news/local/lower-house-financial-committee-discusses-education-ministry-higher-education-ministry |
| S9 | Ocelot starting price ~$15k per feature per year (GetApp) | https://www.getapp.com/education-childcare-software/a/ocelot |
| S10 | Ivy & Ocelot priced by student population (G2) | https://www.g2.com/products/ivy-ocelot/pricing |
| S11 | GPT-5.4 mini / GPT-5 nano / embedding prices (aggregators; verify on OpenAI's pricing page) | https://pricepertoken.com/pricing-page/model/openai-gpt-5.4-mini · https://pricepertoken.com/pricing-page/model/openai-gpt-5-nano |
| S12 | DataReportal Digital 2025 Palestine: 2.3M social media user identities | https://datareportal.com/reports/digital-2025-palestine |
