"""
Generate small FICTIONAL example documents in data/examples/ to smoke-test the pipeline.
"شركة الأفق للبرمجيات" does not exist; every policy and number here is made up.

Each file exercises a different part of the section-based loader:
  hr_policies_2025.pdf    headings detected by FONT SIZE only (no "المادة" words), a long
                          section with numbered clauses (tests splitting), a table, a footer
                          repeated on every page (tests header/footer removal)
  travel_policy.docx      headings from Word styles (Heading 1/2), a table
  it_security_faq.md      markdown headings
  leave_policy_2023.txt   plain text with "المادة N" headings (regex detection) and an OLDER
                          annual-leave rule that conflicts with the 2025 PDF

Run:  python scripts/make_examples.py      (the PDF needs Google Chrome)
Delete data/examples/ once the real documents are in data/raw/.
"""

import json
import subprocess
import tempfile
from pathlib import Path

from docx import Document

OUT = Path(__file__).resolve().parent.parent / "data" / "examples"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Lesson A1/A7: render Arabic PDFs with Chrome and the lam-alef ligature OFF, otherwise
# the text extracts with wrong letters. Lesson A4/A5: no tashkeel, no parentheses.
PDF_CSS = """
@page { size: A4; margin: 2cm 2cm 2.5cm 2cm; }
* { font-family: Tahoma, sans-serif; font-feature-settings: 'rlig' 0, 'liga' 0; }
body { direction: rtl; text-align: right; font-size: 12px; line-height: 1.7; }
h1 { font-size: 22px; } h2 { font-size: 17px; margin-top: 18px; } h3 { font-size: 14px; margin-top: 12px; }
.chapter { page-break-before: always; }
table { border-collapse: collapse; width: 100%; } td, th { border: 1px solid #999; padding: 4px; }
.footer { position: fixed; bottom: -1.5cm; right: 0; font-size: 9px; color: #777; }
"""

REMOTE_CLAUSES = [
    "يحق للموظف الذي أمضى ستة أشهر على الأقل في الشركة أن يطلب العمل عن بعد لمدة لا تزيد عن يومين في الأسبوع، على أن يقدم الطلب عبر نظام الموارد البشرية قبل أسبوع على الأقل من موعد البدء، وأن يحصل على موافقة مديره المباشر خطيا.",
    "لا يشمل العمل عن بعد الموظفين في فترة التجربة، ولا الوظائف التي تتطلب حضورا فعليا مثل الدعم الفني الميداني واستقبال العملاء وإدارة المرافق، ويحدد مدير الإدارة قائمة هذه الوظائف ويراجعها مرة كل سنة.",
    "يلتزم الموظف أثناء العمل عن بعد بساعات العمل الرسمية نفسها، وأن يكون متاحا على أدوات التواصل المعتمدة في الشركة، وأن يرد على الرسائل خلال ثلاثين دقيقة كحد أقصى خلال ساعات العمل.",
    "توفر الشركة للموظف الذي يعمل عن بعد حاسوبا محمولا مزودا ببرنامج الحماية المعتمد، ولا يجوز استخدام أجهزة شخصية للوصول إلى أنظمة الشركة إلا بعد تسجيلها لدى قسم تكنولوجيا المعلومات.",
    "يجب أن يكون اتصال الموظف بأنظمة الشركة من خلال الشبكة الافتراضية الخاصة المعتمدة فقط، ويمنع العمل من الشبكات العامة المفتوحة مثل شبكات المقاهي والمطارات دون تفعيل الشبكة الافتراضية الخاصة.",
    "تدفع الشركة للموظف الذي يعمل عن بعد بدل إنترنت شهريا قيمته 50 شيكلا، ويصرف مع الراتب بشرط ألا يقل عدد أيام العمل عن بعد عن أربعة أيام في الشهر.",
    "يحق للمدير المباشر إلغاء ترتيب العمل عن بعد إذا انخفض أداء الموظف أو تكررت صعوبة التواصل معه، على أن يبلغ الموظف بذلك قبل أسبوع، مع بيان الأسباب كتابيا.",
    "في الحالات الطارئة مثل الإغلاقات أو الظروف الجوية الصعبة يجوز للإدارة العليا السماح بالعمل عن بعد لجميع الموظفين لمدة محددة، ويعلن ذلك عبر البريد الإلكتروني الرسمي للشركة.",
]

PDF_HTML = f"""
<div class="footer">شركة الأفق للبرمجيات - وثيقة داخلية سرية - وثيقة تجريبية خيالية</div>
<h1>دليل سياسات الموارد البشرية - إصدار 2025</h1>
<p>يحدد هذا الدليل حقوق الموظفين وواجباتهم في شركة الأفق للبرمجيات، ويحل محل جميع السياسات السابقة ابتداء من الأول من كانون الثاني 2025.</p>
<h2>الفصل الأول: الإجازات</h2>
<h3>الإجازة السنوية</h3>
<p>يستحق الموظف إجازة سنوية مدفوعة الأجر مدتها 21 يوم عمل، وتصبح 28 يوم عمل بعد إتمام خمس سنوات خدمة متواصلة. لا يجوز ترحيل أكثر من 7 أيام غير مستخدمة إلى السنة التالية.</p>
<h3>الإجازة المرضية</h3>
<p>يستحق الموظف إجازة مرضية مدتها 14 يوما في السنة براتب كامل، بشرط تقديم تقرير طبي معتمد لأي غياب يزيد عن يومين متتاليين.</p>
<h3>إجازة الأمومة والأبوة</h3>
<p>تستحق الموظفة إجازة أمومة مدفوعة الأجر مدتها 70 يوما، ويستحق الموظف إجازة أبوة مدفوعة الأجر مدتها 3 أيام عمل.</p>
<h2 class="chapter">الفصل الثاني: ساعات العمل والعمل عن بعد</h2>
<h3>ساعات العمل الرسمية</h3>
<p>تبدأ ساعات العمل الرسمية الساعة 8:30 صباحا وتنتهي الساعة 4:30 مساء، من الأحد إلى الخميس.</p>
<h3>العمل عن بعد</h3>
{"".join(f"<p>{i}. {c}</p>" for i, c in enumerate(REMOTE_CLAUSES, start=1))}
<h2 class="chapter">الفصل الثالث: البدلات</h2>
<p>تصرف البدلات التالية شهريا مع الراتب:</p>
<table>
<tr><th>البدل</th><th>القيمة الشهرية</th><th>الشرط</th></tr>
<tr><td>بدل مواصلات</td><td>150 شيكل</td><td>لجميع الموظفين</td></tr>
<tr><td>بدل اتصالات</td><td>100 شيكل</td><td>لموظفي المبيعات والدعم</td></tr>
<tr><td>بدل إنترنت</td><td>50 شيكل</td><td>للعاملين عن بعد 4 أيام شهريا على الأقل</td></tr>
</table>
"""


def make_pdf(path: Path) -> None:
    html = f'<html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>{PDF_CSS}</style></head><body>{PDF_HTML}</body></html>'
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "doc.html"
        src.write_text(html, encoding="utf-8")
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={path}", src.as_uri()], check=True, capture_output=True)


def make_docx(path: Path) -> None:
    doc = Document()
    doc.add_heading("سياسة السفر والمصاريف", level=1)
    doc.add_paragraph("تنظم هذه السياسة سفر موظفي شركة الأفق للبرمجيات في مهمات العمل. وثيقة تجريبية خيالية.")
    doc.add_heading("حجز السفر", level=2)
    doc.add_paragraph("يتم حجز تذاكر الطيران والفنادق عن طريق قسم المشتريات فقط، قبل أسبوعين على الأقل من موعد السفر. تكون تذاكر الطيران على الدرجة الاقتصادية لجميع الموظفين.")
    doc.add_heading("المياومات", level=2)
    doc.add_paragraph("يصرف للموظف المسافر مبلغ يومي لتغطية الطعام والتنقل حسب الجدول التالي:")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "الوجهة", "المياومة اليومية"
    for dest, amount in [("داخل فلسطين", "80 شيكل"), ("الأردن", "60 دينار"), ("أوروبا", "120 يورو")]:
        row = table.add_row().cells
        row[0].text, row[1].text = dest, amount
    doc.add_heading("تقديم المطالبات المالية", level=2)
    doc.add_paragraph("يقدم الموظف مطالبة المصاريف مع الفواتير الأصلية خلال 10 أيام عمل من تاريخ العودة، ولا تقبل المطالبات المقدمة بعد ذلك.")
    doc.save(path)


MD_TEXT = """# أسئلة شائعة عن أمن المعلومات

وثيقة تجريبية خيالية لشركة الأفق للبرمجيات.

## كلمات المرور

يجب ألا تقل كلمة المرور عن 12 حرفا وأن تحتوي على أرقام ورموز، ويجب تغييرها كل 90 يوما. يمنع استخدام كلمة المرور نفسها في أكثر من نظام.

## الأجهزة الشخصية

يسمح باستخدام الهاتف الشخصي للوصول إلى البريد الإلكتروني فقط بعد تثبيت تطبيق إدارة الأجهزة المعتمد من قسم تكنولوجيا المعلومات.

## الإبلاغ عن الحوادث الأمنية

عند الاشتباه بأي اختراق أو رسالة تصيد، يجب إبلاغ فريق الأمن خلال ساعة واحدة عبر البريد security@alofoq.example وعدم حذف الرسالة المشبوهة.
"""

TXT_TEXT = """سياسة الإجازات - إصدار 2023
وثيقة تجريبية خيالية لشركة الأفق للبرمجيات.

المادة 1: الإجازة السنوية
يستحق الموظف إجازة سنوية مدفوعة الأجر مدتها 18 يوم عمل، ولا يجوز ترحيل الأيام غير المستخدمة إلى السنة التالية.

المادة 2: الإجازة المرضية
يستحق الموظف إجازة مرضية مدتها 10 أيام في السنة براتب كامل بتقرير طبي.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_pdf(OUT / "hr_policies_2025.pdf")
    make_docx(OUT / "travel_policy.docx")
    (OUT / "it_security_faq.md").write_text(MD_TEXT, encoding="utf-8")
    (OUT / "leave_policy_2023.txt").write_text(TXT_TEXT, encoding="utf-8")
    metadata = {
        "hr_policies_2025.pdf": {"title": "دليل سياسات الموارد البشرية", "version": "2025", "date": "2025-01-01"},
        "travel_policy.docx": {"title": "سياسة السفر والمصاريف", "version": "2024", "date": "2024-03-01"},
        "it_security_faq.md": {"title": "أسئلة شائعة عن أمن المعلومات", "version": "2025", "date": "2025-02-10"},
        "leave_policy_2023.txt": {"title": "سياسة الإجازات", "version": "2023", "date": "2023-01-01"},
    }
    (OUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(metadata)} example documents to {OUT}")


if __name__ == "__main__":
    main()
