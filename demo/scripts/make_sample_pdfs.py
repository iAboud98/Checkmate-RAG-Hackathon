"""
Generate the FICTIONAL sample documents for the demo.

"جامعة النخيل" does not exist. Every rule, number and fee below is made up
so we have something realistic to search over. The documents are designed to
exercise the hard cases judges like to test:

  * student_regulations_2023.pdf vs student_regulations_2025.pdf
        -> the same rules in two versions with some numbers changed (conflict test)
  * computer_engineering_study_plan.pdf
        -> a table of courses (table test)
  * registration_and_fees.pdf
        -> plain lookups (deadlines, fees)

How the PDFs are made: we write each document as HTML and ask headless
Google Chrome to "print" it to PDF. (We tried PyMuPDF's own HTML writer first,
but its Arabic text came back garbled when read back. A good lesson: always
check that text extracts correctly from your PDFs before you index them.)

Note `font-feature-settings: 'rlig' 0` in the CSS: it turns off the special
lam-alef ligature (لا). With it on, Chrome's PDF maps that glyph back to the
wrong letters ("علامة" extracts as "عالمة"), a very common Arabic PDF problem.

Run:  python scripts/make_sample_pdfs.py      (needs Google Chrome installed)
The generated PDFs are already in data/raw/, so you only need this to change them.
"""

import json
import subprocess
import tempfile
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Base styling for every page. dir="rtl" makes the text flow right-to-left,
# and PyMuPDF's HTML engine shapes the Arabic letters correctly.
CSS = """
@page { size: A4; margin: 2cm; }
* { font-family: Tahoma, sans-serif; font-feature-settings: 'rlig' 0, 'liga' 0; }
body { direction: rtl; text-align: right; font-size: 12px; line-height: 1.6; }
h1 { font-size: 20px; color: #12355b; }
h2 { font-size: 14px; color: #12355b; margin-top: 10px; }
.page { page-break-after: always; }
.note { font-size: 9px; color: #888; }
table { border-collapse: collapse; width: 100%; }
td, th { border: 1px solid #999; padding: 4px; }
th { background: #e8eef5; }
"""

# (We left out tashkeel/diacritics and parentheses on purpose: in RTL PDFs they
#  extract out of order or mirrored. Real documents will have them, so expect some noise.)
DISCLAIMER = '<p class="note">وثيقة تجريبية خيالية لأغراض التعلم فقط. جامعة النخيل جامعة غير حقيقية.</p>'

# Each document = file name + metadata + a list of pages (HTML strings).
DOCUMENTS = [
    {
        "file": "student_regulations_2023.pdf",
        "title": "نظام الدراسة لمرحلة البكالوريوس",
        "version": "2023",
        "date": "2023-09-01",
        "pages": [
            """
            <h1>جامعة النخيل - نظام الدراسة لمرحلة البكالوريوس - إصدار 2023</h1>
            <h2>المادة 1: تعريفات</h2>
            <p>المساق: وحدة دراسية لها رقم واسم وعدد من الساعات المعتمدة. الساعة المعتمدة: محاضرة نظرية مدتها خمسون دقيقة أسبوعيا طوال الفصل الدراسي.</p>
            <h2>المادة 2: الحضور والغياب</h2>
            <p>لا يجوز أن تتجاوز نسبة غياب الطالب 15% من مجموع الساعات المقررة للمساق. إذا تجاوز الطالب هذه النسبة دون عذر مقبول يحرم من التقدم للامتحان النهائي ويعتبر راسبا في المساق.</p>
            <h2>المادة 3: العلامات</h2>
            <p>علامة النجاح في المساق هي 60 من 100. تحسب العلامة النهائية من مجموع الأعمال الفصلية والامتحان النهائي، ولا يقل وزن الامتحان النهائي عن 40% من العلامة.</p>
            """,
            """
            <h2>المادة 4: الإنذار الأكاديمي والفصل</h2>
            <p>يوضع الطالب تحت الإنذار الأكاديمي إذا قل معدله التراكمي عن 65. ويفصل الطالب من التخصص إذا بقي تحت الإنذار ثلاثة فصول دراسية متتالية.</p>
            <h2>المادة 5: العبء الدراسي</h2>
            <p>الحد الأقصى للعبء الدراسي هو 18 ساعة معتمدة في الفصل الدراسي العادي، والحد الأدنى 12 ساعة. يجوز للطالب المتفوق الذي لا يقل معدله التراكمي عن 85 تسجيل 21 ساعة معتمدة.</p>
            """,
        ],
    },
    {
        "file": "student_regulations_2025.pdf",
        "title": "نظام الدراسة لمرحلة البكالوريوس",
        "version": "2025",
        "date": "2025-08-15",
        "pages": [
            """
            <h1>جامعة النخيل - نظام الدراسة لمرحلة البكالوريوس - إصدار 2025</h1>
            <p>يحل هذا الإصدار محل إصدار عام 2023 ويعمل به ابتداء من العام الأكاديمي 2025/2026 فصاعدا.</p>
            <h2>المادة 1: تعريفات</h2>
            <p>المساق: وحدة دراسية لها رقم واسم وعدد من الساعات المعتمدة. الساعة المعتمدة: محاضرة نظرية مدتها خمسون دقيقة أسبوعيا طوال الفصل الدراسي.</p>
            <h2>المادة 2: الحضور والغياب</h2>
            <p>لا يجوز أن تتجاوز نسبة غياب الطالب 20% من مجموع الساعات المقررة للمساق. إذا تجاوز الطالب هذه النسبة دون عذر مقبول يحرم من التقدم للامتحان النهائي ويعتبر راسبا في المساق.</p>
            <h2>المادة 3: العلامات</h2>
            <p>علامة النجاح في المساق هي 60 من 100. تحسب العلامة النهائية من مجموع الأعمال الفصلية والامتحان النهائي، ولا يقل وزن الامتحان النهائي عن 40% من العلامة.</p>
            """,
            """
            <h2>المادة 4: الإنذار الأكاديمي والفصل</h2>
            <p>يوضع الطالب تحت الإنذار الأكاديمي إذا قل معدله التراكمي عن 68. ويفصل الطالب من التخصص إذا بقي تحت الإنذار فصلين دراسيين متتاليين.</p>
            <h2>المادة 5: العبء الدراسي</h2>
            <p>الحد الأقصى للعبء الدراسي هو 18 ساعة معتمدة في الفصل الدراسي العادي، والحد الأدنى 12 ساعة. يجوز للطالب المتفوق الذي لا يقل معدله التراكمي عن 80 تسجيل 21 ساعة معتمدة.</p>
            <h2>المادة 6: التعلم عن بعد</h2>
            <p>يجوز أن تدرس نسبة لا تزيد عن 25% من مساقات الخطة الدراسية عن بعد، بشرط موافقة مجلس الكلية.</p>
            """,
        ],
    },
    {
        "file": "computer_engineering_study_plan.pdf",
        "title": "الخطة الدراسية لتخصص هندسة الحاسوب",
        "version": "2024",
        "date": "2024-06-01",
        "pages": [
            """
            <h1>جامعة النخيل - الخطة الدراسية لتخصص هندسة الحاسوب</h1>
            <p>يتطلب الحصول على درجة البكالوريوس في هندسة الحاسوب إنهاء 160 ساعة معتمدة بنجاح، منها 21 ساعة متطلبات جامعة و139 ساعة متطلبات تخصص.</p>
            <h2>مساقات التخصص الإجبارية</h2>
            <table>
              <tr><th>رقم المساق</th><th>اسم المساق</th><th>الساعات المعتمدة</th><th>المتطلب السابق</th></tr>
              <tr><td>CPE101</td><td>مقدمة في البرمجة</td><td>3</td><td>لا يوجد</td></tr>
              <tr><td>CPE201</td><td>هياكل البيانات</td><td>3</td><td>CPE101</td></tr>
              <tr><td>CPE210</td><td>التصميم المنطقي الرقمي</td><td>4</td><td>لا يوجد</td></tr>
              <tr><td>CPE310</td><td>أنظمة التشغيل</td><td>3</td><td>CPE201</td></tr>
              <tr><td>CPE320</td><td>شبكات الحاسوب</td><td>3</td><td>CPE310</td></tr>
              <tr><td>CPE330</td><td>قواعد البيانات</td><td>3</td><td>CPE201</td></tr>
              <tr><td>CPE490</td><td>مشروع التخرج 1</td><td>3</td><td>إنهاء 120 ساعة معتمدة</td></tr>
              <tr><td>CPE491</td><td>مشروع التخرج 2</td><td>3</td><td>CPE490</td></tr>
            </table>
            <h2>التدريب العملي</h2>
            <p>يلتزم الطالب بتدريب عملي مدته ثمانية أسابيع في مؤسسة معتمدة بعد إنهاء 100 ساعة معتمدة على الأقل.</p>
            """,
        ],
    },
    {
        "file": "registration_and_fees.pdf",
        "title": "دليل التسجيل والرسوم الجامعية",
        "version": "2025",
        "date": "2025-08-20",
        "pages": [
            """
            <h1>جامعة النخيل - دليل التسجيل والرسوم الجامعية</h1>
            <h2>مواعيد التسجيل</h2>
            <p>يتم التسجيل المبكر قبل بداية الفصل الدراسي بأسبوعين عبر بوابة الطالب الإلكترونية.</p>
            <p>فترة السحب والإضافة: خلال الأسبوع الأول من بداية الفصل الدراسي فقط، ولا تظهر المساقات المسحوبة في هذه الفترة على كشف العلامات.</p>
            <p>الانسحاب من المساق: يجوز للطالب الانسحاب من مساق حتى نهاية الأسبوع العاشر من الفصل، ويسجل له في كشف العلامات رمز W دون أن يدخل في المعدل.</p>
            """,
            """
            <h2>الرسوم الجامعية</h2>
            <p>سعر الساعة المعتمدة في كلية الهندسة 45 دينارا أردنيا، وفي باقي الكليات 35 دينارا أردنيا.</p>
            <p>رسوم التسجيل الفصلية الثابتة 50 دينارا أردنيا تدفع مع القسط الأول.</p>
            <p>غرامة التسجيل المتأخر 20 دينارا أردنيا.</p>
            <h2>الخصومات</h2>
            <p>يحصل الأخوة المسجلون في الجامعة في نفس الفصل على خصم 10% من رسوم الساعات المعتمدة لكل منهم.</p>
            """,
        ],
    },
]


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def make_pdf(doc: dict) -> None:
    # One <div class="page"> per page; the CSS forces a page break after each.
    pages = "".join(f'<div class="page">{html}{DISCLAIMER}</div>' for html in doc["pages"])
    full_html = (
        f'<html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>{doc["title"]}</title>'
        f"<style>{CSS}</style></head><body>{pages}</body></html>"
    )
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "doc.html"
        html_path.write_text(full_html, encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={RAW_DIR / doc['file']}", html_path.as_uri()],
            check=True, capture_output=True,
        )


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for doc in DOCUMENTS:
        make_pdf(doc)
        # metadata.json tells the indexer which version/date each file is.
        # This is what lets the system prefer the NEWER rules when two docs disagree.
        metadata[doc["file"]] = {"title": doc["title"], "version": doc["version"], "date": doc["date"]}
        print(f"wrote {doc['file']} ({len(doc['pages'])} pages)")
    (RAW_DIR / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote metadata.json")


if __name__ == "__main__":
    main()
