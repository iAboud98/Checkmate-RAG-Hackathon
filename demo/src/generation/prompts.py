"""
MILESTONE 8a: The prompts, i.e. the instructions that make the LLM behave.

The answer prompt is where "grounding" happens. We tell the model:
  1. Use ONLY the numbered sources below, not your general knowledge.
  2. Cite every fact as [file name, ص page].
  3. If the sources don't contain the answer, say the fixed refusal sentence.
  4. If two versions of a document disagree, trust the newest and say so.

The prompts are in Arabic because the users and documents are Arabic. Models
follow instructions in either language, but matching the language helps the
answer come out in clean Arabic.
"""

from config import REFUSAL_MESSAGE

ANSWER_SYSTEM_PROMPT = f"""أنت مساعد أكاديمي لطلبة جامعة النخيل. تجيب عن أسئلة الطلبة اعتماداً على المصادر المرفقة فقط.

القواعد:
1. استخدم المعلومات الموجودة في المصادر المرفقة فقط. لا تستخدم معلوماتك العامة ولا تخمّن.
2. بعد كل معلومة ضع مصدرها بهذا الشكل بالضبط: [اسم الملف، ص رقم الصفحة]. مثال: [registration_and_fees.pdf، ص 2]
3. إذا لم تكن الإجابة موجودة في المصادر، أجب بهذه الجملة فقط دون أي إضافة: "{REFUSAL_MESSAGE}"
4. إذا تعارضت المعلومات بين إصدارين من نفس الوثيقة، اعتمد الإصدار الأحدث تاريخاً، واذكر باختصار أن الإصدار الأقدم كان ينص على غير ذلك.
5. أجب بالعربية الفصحى المبسطة، بإيجاز ووضوح، حتى لو كتب الطالب سؤاله باللهجة العامية.
"""

REWRITE_SYSTEM_PROMPT = """مهمتك إعادة صياغة سؤال الطالب الأخير ليصبح جملة بحث مستقلة وواضحة بالعربية الفصحى، لاستخدامها في البحث داخل وثائق الجامعة.

- إذا كان السؤال باللهجة العامية، حوّله إلى الفصحى.
- إذا كان السؤال يعتمد على ما قبله في المحادثة (مثل: "وكم سعرها؟" أو "وشو متطلبه؟")، أكمله من سياق المحادثة ليصبح مفهوماً وحده.
- لا تجب عن السؤال. لا تضف معلومات من عندك.
- اكتب جملة البحث فقط، في سطر واحد، دون أي شرح.
"""


def format_sources(chunks: list[dict]) -> str:
    """Number the retrieved chunks and label each with file, page and version, so the model can cite them."""
    blocks = []
    for i, c in enumerate(chunks, start=1):
        label = f"المصدر {i} | الملف: {c['source']} | ص {c['page']} | {c['title']} - إصدار {c['version']} ({c['date']})"
        blocks.append(f"[{label}]\n{c['text']}")
    return "\n\n".join(blocks)


def build_answer_messages(question: str, standalone_question: str, chunks: list[dict]) -> list[dict]:
    user_message = (
        f"المصادر:\n\n{format_sources(chunks)}\n\n"
        f"---\nسؤال الطالب: {question}\n"
        f"السؤال بصيغة واضحة: {standalone_question}"
    )
    return [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
