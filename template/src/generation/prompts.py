"""
Prompts. Grounding rules are fixed; domain wording comes from domain.py.

Each retrieved section is shown to the model as a NUMBERED source ([1], [2]...) with its
document title, section, page, breadcrumb path and version/date. The model cites the number
(Perplexity-style); the app turns [n] into a clickable chip and the eval expands it back to the
full label [document، section، ص N]. Numbers are short, so the model copies them reliably.
"""

import domain
from src.ingest.sections import citation_label

_BASE_RULES = [
    "استخدم المعلومات الموجودة في المصادر المرفقة فقط. لا تستخدم معلوماتك العامة ولا تخمّن.",
    "بعد كل معلومة ضع رقم مصدرها بين قوسين مربعين مثل [1] أو [2][3]، كما هو مكتوب في سطر \"الاستشهاد\". لا تكتب أسماء الملفات.",
    f"إذا لم تكن الإجابة موجودة في المصادر، أجب بهذه الجملة فقط دون أي إضافة: \"{domain.REFUSAL_MESSAGE}\"",
    "إذا تعارضت المعلومات بين إصدارين أو وثيقتين، اعتمد الأحدث تاريخاً، واذكر باختصار أن الإصدار الأقدم كان ينص على غير ذلك.",
    "أجب بالعربية الفصحى المبسطة، بإيجاز ووضوح، حتى لو كان السؤال باللهجة العامية.",
]


def answer_system_prompt() -> str:
    rules = _BASE_RULES + domain.EXTRA_RULES
    numbered = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, start=1))
    return (f"أنت {domain.ASSISTANT_NAME}، تجيب عن أسئلة {domain.AUDIENCE} حول {domain.DOMAIN_DESCRIPTION}، "
            f"اعتماداً على المصادر المرفقة فقط.\n\nالقواعد:\n{numbered}")


def format_sources(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        version = f"إصدار {c['version']} ({c['date']})" if c["version"] else "بدون إصدار"
        blocks.append(
            f"### المصدر {i}\n"
            f"الاستشهاد: [{i}]  ({citation_label(c)})\n"
            f"الموقع في الوثيقة: {c['section_path']}\n"
            f"الوثيقة: {c['doc_title']} - {version}\n"
            f"{c['text']}"
        )
    return "\n\n".join(blocks)


def build_answer_messages(question: str, standalone_question: str, chunks: list[dict]) -> list[dict]:
    user = (f"المصادر:\n\n{format_sources(chunks)}\n\n---\n"
            f"سؤال المستخدم: {question}\nالسؤال بصيغة واضحة: {standalone_question}")
    return [{"role": "system", "content": answer_system_prompt()}, {"role": "user", "content": user}]


def rewrite_system_prompt() -> str:
    examples = "\n\n".join(
        f"المحادثة السابقة: {e['history'] or '(لا يوجد)'}\nالسؤال: {e['question']}\nجملة البحث: {e['rewritten']}"
        for e in domain.REWRITE_EXAMPLES
    )
    # Note: we deliberately do NOT tell the rewriter what the domain is. When we did, it
    # pulled off-topic questions into the domain ("كيف أطبخ المقلوبة؟" became a question
    # about workplace food policies) and they slipped past the refusal gate (lesson B5).
    return f"""مهمتك تحويل سؤال المستخدم الأخير إلى جملة بحث مستقلة وواضحة بالعربية الفصحى.

- إذا كان السؤال باللهجة العامية، حوّله إلى الفصحى.
- إذا كان السؤال يعتمد على ما قبله في المحادثة، أكمله من السياق ليصبح مفهوماً وحده.
- إذا كان السؤال واضحاً أصلاً، أعده كما هو تقريباً.
- لا تجب عن السؤال، ولا تضف أي تفاصيل أو أسماء أو شروط غير موجودة في السؤال أو المحادثة.
- لا تغيّر موضوع السؤال أبداً، حتى لو بدا بعيداً عن موضوع المحادثة.
- اكتب جملة البحث فقط في سطر واحد.

أمثلة:

{examples}"""
