"""
THE ONE FILE TO EDIT FOR THE HACKATHON PROBLEM.

Problem #1: Smart academic advisor (المرشد الذكي) for Birzeit University.
Everything domain-specific lives here: who the assistant is, who it serves, the refusal
sentence, UI text, the FAQ list, which dataset documents we import, and examples that
teach the query rewriter.
"""

# --- Identity ------------------------------------------------------------------
BRAND = "Checkmate"
ASSISTANT_NAME = "المرشد الذكي (Checkmate)"
DOMAIN_DESCRIPTION = ("أنظمة وتعليمات جامعة بيرزيت الأكاديمية والطلابية، ودليل البكالوريوس، "
                      "والخطط الدراسية لبرامج كلية الهندسة")
AUDIENCE = "طلبة جامعة بيرزيت ومرشديهم الأكاديميين"

# Exact sentence when the documents don't contain the answer (also used to detect refusals).
REFUSAL_MESSAGE = "عذراً، لم أجد هذه المعلومة في وثائق جامعة بيرزيت المتاحة لدي."

DISCLAIMER = "للإرشاد فقط. القرار النهائي لدائرة التسجيل والمرشد الأكاديمي."

# Extra rules for the answer prompt. One rule per string.
EXTRA_RULES: list[str] = [
    "الطالب طالب بكالوريوس ما لم يذكر غير ذلك؛ إذا ذكرت المصادر أحكاماً لمراحل أخرى فاعتمد أحكام البكالوريوس.",
    "اكتب رموز المساقات كما هي في المصادر (مثل ENCS3350) ولا تخترع رموزاً أو أسماء مساقات.",
    "إذا وُجد مصدر بعنوان \"ملف الطالب\" فهو سجل الطالب نفسه (المساقات التي أنهاها)؛ استخدمه للإجابة عن أسئلته الشخصية "
    "مع خطة التخصص، ولا تفترض أنه أنهى مساقاً غير مذكور فيه.",
]

# --- UI ------------------------------------------------------------------------
APP_TITLE = "Checkmate · المرشد الذكي"
APP_ICON = "♞"
AVATAR = "♟️"   # chat avatar: Streamlit only accepts real emoji there, and ♞ is not one
APP_TAGLINE = "مرشدك الأكاديمي في جامعة بيرزيت"
APP_SUBTITLE = "اسأل بلهجتك عن الأنظمة والتسجيل وخطتك الدراسية. الإجابات من وثائق بيرزيت الرسمية فقط، مع رقم الصفحة."
EXAMPLE_QUESTIONS = [
    "قديش لازم يكون معدلي عشان ما آخذ إنذار أكاديمي؟",
    "إذا انسحبت من مساق شو بصير بعلامتي؟",
    "شو المتطلب السابق لمساق ENCS3350؟",
    "شو ضايلي مساقات عشان أتخرج؟",
]

# FAQ tab: answered ahead of time by the same RAG pipeline (scripts/build_faq.py), grouped by topic.
FAQ_QUESTIONS = {
    "الإنذار والفصل الأكاديمي": [
        "متى يوضع الطالب تحت الإنذار الأكاديمي؟",
        "متى يفصل الطالب من الجامعة لأسباب أكاديمية؟",
    ],
    "التسجيل والانسحاب": [
        "ما هو الحد الأعلى والأدنى للساعات المعتمدة التي يسجلها الطالب في الفصل؟",
        "ما هي شروط الانسحاب من مساق؟",
        "هل يمكن للطالب إعادة دراسة مساق نجح فيه؟",
    ],
    "الحضور والامتحانات": [
        "ما هي نسبة الغياب المسموح بها في المساق؟",
        "ماذا يحدث إذا تغيب الطالب عن الامتحان النهائي بعذر؟",
    ],
    "التخرج والشهادات": [
        "ما هي شروط التخرج من درجة البكالوريوس؟",
        "كيف أحصل على بدل ضائع لشهادة البكالوريوس؟",
    ],
    "المنح والرسوم والسكن": [
        "ما هي شروط منح التفوق الأكاديمي لطلبة البكالوريوس؟",
        "ما هي تعليمات العمل الجزئي المدفوع الأجر لطلبة البكالوريوس؟",
        "ما هي شروط الإقامة في سكن الطالبات؟",
    ],
    "النزاهة والسلوك": [
        "ما هي عقوبة الغش في الامتحان؟",
        "ما هي سياسة الجامعة في استخدام الذكاء الاصطناعي؟",
    ],
    "هندسة الحاسوب": [
        "كم عدد الساعات المعتمدة المطلوبة لبكالوريوس هندسة الحاسوب؟",
        "ما هي مساقات السنة الأولى في خطة هندسة الحاسوب؟",
    ],
}

# Words that mean "this is about MY study plan" -> the student's profile becomes a source.
PLAN_KEYWORDS = ["ضايل", "باقي", "متبقي", "المتبقية", "أتخرج", "اتخرج", "تخرجي", "خطتي", "أسجل", "اسجل",
                 "آخذ", "اخذ", "بقدر", "أقدر", "اقدر", "متطلب", "مساقاتي", "الفصل الجاي", "الفصل القادم", "ساعاتي"]

# --- Which dataset documents we import (scripts/import_dataset.py) ---------------
STUDENT_CATEGORIES = {
    "أنظمة وتعليمات تتعلق بالطلبة",
    "أنظمة وتعليمات أكاديمية",
    "تعليمات منح درجتي الماجستير والدبلوم العالي",
}
STUDENT_TITLE_KEYWORDS = ["الطلبة", "الطالب", "البكالوريوس", "الرسوم", "سكن الرياض", "السكن الجامعي للطالبات",
                          "الإعفاءات", "الذكاء الاصطناعي", "الأمانة الأكاديمية", "مدونة السلوك", "التقويم السنوي",
                          "التبادل", "القانون العام لجامعة بيرزيت", "إدارة الحرم الجامعي", "صندوق دعم الطالب"]
# Staff-only documents that match a keyword above by accident.
STAFF_TITLE_WORDS = ["للعاملين", "الموظفين", "لموظفي", "الهيئة الأكاديمية", "الهدايا", "أعباء"]
# Checkmate serves undergraduates: graduate rules (other probation GPAs) were outranking the bachelor
# rules in the eval (q05, q09), so they are left out on purpose.
GRADUATE_TITLE_WORDS = ["الماجستير", "الدكتوراه", "الدكتوراة", "الدراسات العليا", "دكتور في الطب", "الدبلوم"]

# --- Query rewriting examples (few-shot) ---------------------------------------
# Teach the rewriter the domain's vocabulary: dialect -> formal, follow-up -> standalone,
# and "already clear -> keep as is" (stops it from adding details, lesson B4).
REWRITE_EXAMPLES = [
    {"history": "", "question": "قديش لازم يكون معدلي عشان ما آخذ إنذار؟",
     "rewritten": "ما هو المعدل التراكمي الذي يوضع الطالب دونه تحت الإنذار الأكاديمي؟"},
    {"history": "", "question": "إذا انسحبت من مادة شو بصير؟",
     "rewritten": "ما هي أحكام الانسحاب من مساق وأثره على علامة الطالب؟"},
    {"history": "الطالب: شو المتطلب السابق لمساق ENCS3350؟\nالمساعد: المتطلب السابق هو ENCS2380 و ENEE2360.",
     "question": "وكم ساعة إله؟",
     "rewritten": "كم عدد الساعات المعتمدة لمساق ENCS3350؟"},
    {"history": "", "question": "ما هي شروط الانسحاب من الجامعة؟",
     "rewritten": "ما هي شروط الانسحاب من الجامعة؟"},
    # Off-topic stays off-topic, so the refusal gate can catch it (lesson B5).
    {"history": "", "question": "مين رح يربح كأس العالم؟",
     "rewritten": "من سيفوز بكأس العالم؟"},
]
