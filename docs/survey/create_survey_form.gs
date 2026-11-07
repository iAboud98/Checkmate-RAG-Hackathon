/**
 * Team Checkmate · IEEE RAG Hackathon
 * Builds the quick Birzeit student survey (evidence for slide 1) as a Google Form.
 *
 * How to run:
 *   1. Open https://script.google.com → New project
 *   2. Delete the sample code, paste this whole file, click Save
 *   3. Choose the function "createSurvey" and click Run, then approve the permissions
 *   4. Open "Execution log": it prints the share link (send to students) and the edit link
 *
 * Privacy: no names, no emails, no sign-in required.
 */
function createSurvey() {
  var form = FormApp.create('استبيان سريع (أقل من دقيقة): الإرشاد الأكاديمي في بيرزيت');

  form.setDescription(
    'إحنا فريق Checkmate في هاكاثون IEEE، بنبني "المرشد الذكي" لطلاب بيرزيت. ' +
    'الاستبيان بدون اسم أو إيميل. شكراً إلك! 🙏'
  );

  // No emails, no login, one page, no "submit another response" link.
  try { form.setCollectEmail(false); } catch (e) {}
  form.setLimitOneResponsePerUser(false); // true would force students to sign in
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(false);
  form.setProgressBar(false);
  form.setConfirmationMessage('شكراً كتير! جوابك رح يساعدنا نبني مرشد أحسن لطلاب بيرزيت 💙');

  // 1
  form.addMultipleChoiceItem()
    .setTitle('سنتك الدراسية؟')
    .setChoiceValues(['أولى', 'ثانية', 'ثالثة', 'رابعة', 'خامسة أو أكثر'])
    .setRequired(true);

  // 2  → slide-1 evidence (prerequisites)
  form.addMultipleChoiceItem()
    .setTitle('هل صار معك إنك ما عرفت إذا مساق إله متطلب سابق، أو سجلت مساق وطلع ناقصك متطلبه؟')
    .setChoiceValues(['نعم، صار معي', 'مرة أو مرتين تقريباً', 'لا، ولا مرة'])
    .setRequired(true);

  // 3  → current alternatives (competitors slide)
  form.addMultipleChoiceItem()
    .setTitle('لما يكون عندك سؤال عن خطتك الدراسية أو الأنظمة، وين بتدور أول إشي؟')
    .setChoiceValues([
      'دليل الطالب / ملفات الأنظمة (PDF)',
      'المرشد الأكاديمي',
      'أصحابي أو جروبات واتساب وفيسبوك',
      'موقع الجامعة أو ريتاج',
      'ChatGPT أو أي AI'
    ])
    .setRequired(true);

  // 4  → slide-1 evidence (time lost)
  form.addMultipleChoiceItem()
    .setTitle('عادةً قديش بياخد معك وقت لتلاقي جواب أكيد؟')
    .setChoiceValues(['أقل من 10 دقائق', '10 إلى 30 دقيقة', 'من ساعة ليوم', 'أكثر من يوم'])
    .setRequired(true);

  // 5  → which pains matter most
  form.addCheckboxItem()
    .setTitle('شو أصعب المواضيع اللي بتلاقيلها جواب؟ (ممكن تختار أكثر من وحدة)')
    .setChoiceValues([
      'المتطلبات السابقة',
      'الخطة الدراسية وشو ضايلي للتخرج',
      'الانسحاب من مساق أو فصل',
      'الإنذار الأكاديمي',
      'التحويل بين التخصصات'
    ])
    .showOtherOption(true)
    .setRequired(true);

  // 6  → slide-1 evidence (cost of wrong info)
  form.addMultipleChoiceItem()
    .setTitle('هل صار وأخذت معلومة غلط (من صاحب أو جروب) وأثرت على تسجيلك أو معدلك؟')
    .setChoiceValues(['نعم', 'لا'])
    .setRequired(true);

  // 7  → demand
  form.addMultipleChoiceItem()
    .setTitle('لو في مرشد ذكي بجاوبك بالعربي (حتى بالعامية) من أنظمة بيرزيت الرسمية، ويعطيك المصدر ورقم الصفحة، قديش ممكن تستخدمه؟')
    .setChoiceValues(['أكيد رح أستخدمه', 'يمكن', 'لا'])
    .setRequired(true);

  // 8  → channels (marketing slide)
  form.addMultipleChoiceItem()
    .setTitle('وين بتفضّل تستخدمه؟')
    .setChoiceValues(['موقع ويب', 'واتساب', 'تطبيق موبايل'])
    .setRequired(true);

  // Newer Forms may start unpublished; make sure it accepts responses.
  try { form.setPublished(true); } catch (e) {}
  form.setAcceptingResponses(true);

  var shareUrl = form.getPublishedUrl();
  try { shareUrl = form.shortenFormUrl(shareUrl); } catch (e) {}

  Logger.log('SHARE with students: ' + shareUrl);
  Logger.log('EDIT / see responses: ' + form.getEditUrl());
}
