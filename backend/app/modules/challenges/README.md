# قسم سرى: التحديات والـFlags والنقاط

**الـBranch:** `feature/challenges-analytics`
**الميزة الأولى:** إنشاء تحدي جديد، فحص الـFlag، واحتساب النقاط.
**المتطلبات من تقرير GP1:** FR3 (تصفح وتصنيف التحديات)، FR4 (تسليم الـFlag والتحقق منه)، FR11 (الدكتور يضيف تحدي ويحدد النوع والصعوبة والنقاط).

---

## 1. شو بتعمل الميزة؟

1. **الدكتور (Instructor)** بضيف تحدي جديد: عنوان، وصف، نوع، صعوبة، نقاط، والـFlag الصحيح.
2. **الطالب (Student)** بشوف قائمة التحديات، وبقدر يفلترها حسب النوع أو الصعوبة، وبشوف إذا حل كل تحدي أو لا.
3. الطالب بسلّم الـFlag، والنظام برد فورًا: صح أو غلط، كم نقطة أخذ، ومجموع نقاطه، ورقم المحاولة.
4. الطالب بشوف مجموع نقاطه والتحديات اللي حلها.
5. الدكتور بشوف ترتيب الطلاب حسب النقاط (Leaderboard).

## 2. القواعد اللي طبقناها

| القاعدة | التفاصيل |
|---|---|
| أنواع التحديات (Category) | `Web`، `Network`، `Forensics`، `Cryptography`، `Reverse Engineering` فقط. أي نوع ثاني بنرفضه. |
| الصعوبة (Difficulty) | `Easy`، `Medium`، `Hard` فقط. |
| النقاط | الدكتور بحددها (من 10 لـ2000). إذا تركها فاضية، بتنحط تلقائيًا: Easy = 100، Medium = 200، Hard = 300. |
| شكل الـFlag | لازم يكون بالشكل `NEXIS{...}` وبدون مسافات، مثل `NEXIS{caesar_shift_3}`. هيك الدكتور ما بغلط بالكتابة. |
| تخزين الـFlag | الـFlag ما بنخزنه كنص، بنخزن **Hash** إله (مثل كلمات السر). إذا انسرقت قاعدة البيانات، الحلول ما بتنكشف. |
| إخفاء الـFlag | ولا أي رد من الـAPI بيرجع الـFlag أو الـHash. |
| المسافات | إذا الطالب نسخ الـFlag مع مسافة قبله أو بعده، بنشيلها قبل الفحص. |
| حالة الأحرف | الفحص بيفرق بين الأحرف الكبيرة والصغيرة (`nexis{...}` غلط). |
| النقاط مرة وحدة | إذا حل الطالب نفس التحدي مرة ثانية، ما بياخذ نقاط إضافية، وما بنسجلها كمحاولة جديدة. |
| عدم التكرار | ما بنقدر نضيف تحديين بنفس العنوان (حتى لو اختلفت الأحرف الكبيرة والصغيرة). |
| الصلاحيات | بس الدكتور بيضيف تحديات وبيشوف الـLeaderboard. الطالب بشوف نقاطه هو بس. |

## 3. الـAPIs (الـEndpoints)

| الطريقة | الرابط | مين بيستخدمه | شو بعمل |
|---|---|---|---|
| `POST` | `/api/challenges` | الدكتور | إضافة تحدي جديد |
| `GET` | `/api/challenges?category=...&difficulty=...` | الكل | قائمة التحديات مع فلترة، وكل تحدي فيه `solved` (true/false) |
| `GET` | `/api/challenges/{id}` | الكل | تفاصيل تحدي واحد |
| `POST` | `/api/challenges/{id}/submit` | الطالب | تسليم Flag واحتساب النقاط |
| `GET` | `/api/challenges/my-score` | الطالب | مجموع نقاطي والتحديات اللي حليتها |
| `GET` | `/api/challenges/leaderboard` | الدكتور | ترتيب الطلاب حسب النقاط |

مثال على رد تسليم Flag صحيح:

```json
{
  "correct": true,
  "already_solved": false,
  "points_awarded": 150,
  "total_score": 150,
  "attempt_number": 2,
  "message": "Correct flag! +150 points"
}
```

## 4. شو الملفات اللي تغيرت؟

| الملف | التغيير |
|---|---|
| `backend/app/modules/challenges/router.py` | كل منطق الميزة: التحقق من البيانات، النقاط، فحص الـFlag، النقاط الكلية، الـLeaderboard. |
| `backend/tests/test_challenges.py` | ملف جديد فيه 17 اختبار تلقائي للميزة. |
| `backend/app/modules/challenges/README.md` | هاد الملف (التوثيق). |

**ما عدّلنا أي ملف مشترك:** لا `main.py`، ولا `models.py`، ولا إعدادات قاعدة البيانات. النقاط بتنحسب من جدول `submissions` الموجود أصلًا، فما احتجنا نغير الجداول.

## 5. كيف اختبرنا الشغل؟

**أ. اختبارات تلقائية (pytest):**

```bash
cd backend
.venv/bin/python -m pytest -v tests/test_challenges.py   # على Windows: .\.venv\Scripts\python.exe -m pytest -v tests/test_challenges.py
```

النتيجة: **17 passed** لاختبارات الميزة، و**18 passed** لكل اختبارات المشروع.
كمان جربنا ندمج شغلنا مع Branch جويا (`feature/ai-rag`) وBranch حسام (`feature/docker-labs`): ما في Conflicts، وكل الاختبارات مع بعض **45 passed**.

**ب. تجربة يدوية على السيرفر الحقيقي (Swagger):** الخطوات بالتفصيل بالقسم 6.

## 6. خطوات التجربة اليدوية (Swagger)

1. شغّل السيرفر وافتح `http://127.0.0.1:8000/docs`.
2. **سجّل دخول كدكتور:** `POST /api/auth/login` بإيميل وكلمة سر الدكتور (من ملف `backend/local-instructor-credentials.txt`). انسخ قيمة `access_token`.
3. اضغط **Authorize** فوق، والصق الـtoken **لحاله بدون كلمة Bearer** (Swagger بيضيفها لحاله)، وبعدين Authorize ثم Close.
4. **أضف تحدي:** `POST /api/challenges` ← Try it out ← المثال جاهز (Caesar Cipher Breaker، 150 نقطة) ← Execute. المتوقع: `201` والرد ما فيه الـFlag.
5. اضغط Authorize ← Logout. سجّل طالب جديد من `POST /api/auth/register`، وبعدين login، وحط الـtoken تبعه بـAuthorize.
6. **سلّم Flag غلط** على `POST /api/challenges/{challenge_id}/submit` (حط بـ`challenge_id` رقم الـ`id` اللي رجع بالخطوة 4): المتوقع `correct: false` و`points_awarded: 0`.
7. **سلّم الـFlag الصحيح** `NEXIS{caesar_shift_3}`: المتوقع `correct: true` و`points_awarded: 150`.
8. **سلّمه مرة ثانية:** المتوقع `already_solved: true` و`points_awarded: 0` والمجموع ما بتغير.
9. `GET /api/challenges/my-score`: بيطلع المجموع والتحديات المحلولة.
10. ارجع للدكتور وافتح `GET /api/challenges/leaderboard`: بيطلع ترتيب الطلاب.

## 7. شو الخطوات الجاية؟ (مش ضمن هاي الميزة)

- تعديل وحذف (أو إخفاء) التحديات من الدكتور.
- تسجيل الوقت اللي أخذه الطالب لكل تحدي (من أول ما يفتحه لحد ما يحله).
- Behavioral Analytics: متوسط وقت الحل، نسبة الحل من أول محاولة، استخدام التلميحات، لكل تحدي ولكل طالب (FR7، FR8).
