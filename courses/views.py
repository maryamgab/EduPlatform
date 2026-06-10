import random
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from .forms import AttachmentForm, CourseForm, LessonForm, ModuleForm
from .models import Course, Enrollment, Lesson, LessonProgress, Module, LessonBlock, Quiz, Question, Choice, MatchPair, QuizAttempt, Answer
from django.contrib import messages
from .block_forms import LessonBlockForm
from django.db.models import Max, Sum, Q, Count
from .formsets import LessonBlockFormSet
from .quiz_forms import QuizForm, QuestionForm, ChoiceFormSet, MatchPairFormSet
from django.db import transaction


PRIVATE_COURSE_SESSION_KEY = "private_course_access_ids"

# получение из сессии список ID приватных курсов, к которым пользователю уже был выдан доступ.
def _get_private_course_access_ids(request):
    return set(request.session.get(PRIVATE_COURSE_SESSION_KEY, []))

# добавление ID приватного курса в сессию, тобы пользователь мог открыть его без повторного ввода кода и пароля.
def _grant_private_course_access(request, course: Course):
    access_ids = _get_private_course_access_ids(request)
    access_ids.add(course.id)
    request.session[PRIVATE_COURSE_SESSION_KEY] = sorted(access_ids)
    request.session.modified = True

# проверка, может ли пользователь открыть приватный курс:
# курс должен быть публичным, либо пользователь должен быть владельцем, записанным участником
# или иметь ранее выданный доступ через сессию.
def _can_access_private_course(request, course: Course) -> bool:
    if not course.is_private:
        return True

    if request.user.is_authenticated:
        if course.owner_id == request.user.id:
            return True
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return True

    return course.id in _get_private_course_access_ids(request)

# формирирование каталога курсов:
# вывод только опубликованных и неприватных курсов,
# поиск, фильтрацию по категории и подкатегории,
# сортировка по выбранному критерию.
def course_list(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    subcategory = request.GET.get("subcategory", "").strip()
    sort = request.GET.get("sort", "").strip()

    courses = Course.objects.filter(is_published=True, is_private=False).annotate(
        students_count=Count("enrollments", distinct=True)
    )

    if query:
        courses = courses.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )

    if category:
        courses = courses.filter(category=category)

    if subcategory:
        courses = courses.filter(subcategory=subcategory)

    if sort == "popular":
        courses = courses.order_by("-students_count", "-created_at")
    elif sort == "newest":
        courses = courses.order_by("-created_at")
    elif sort == "oldest":
        courses = courses.order_by("created_at")
    elif sort == "title_asc":
        courses = courses.order_by("title")
    elif sort == "title_desc":
        courses = courses.order_by("-title")
    else:
        courses = courses.order_by("-students_count", "-created_at")

    return render(request, "courses/course_list.html", {
        "courses": courses,
        "query": query,
        "selected_category": category,
        "selected_subcategory": subcategory,
        "selected_sort": sort,
        "categories": Course.Category.choices,
    })

# обработка входа в приватный курс по коду и паролю
@require_POST
@csrf_protect
def private_course_access(request):
    access_code = Course.normalize_access_code(request.POST.get("access_code", ""))
    access_password = (request.POST.get("access_password", "") or "").strip()

    if not access_code or not access_password:
        messages.error(request, "Введите код и пароль приватного курса.")
        return redirect("course_list")

    course = Course.objects.filter(
        is_published=True,
        is_private=True,
        access_code=access_code,
    ).first()

    if not course or not course.check_access_password(access_password):
        messages.error(request, "Неверный код или пароль приватного курса.")
        return redirect("course_list")

    _grant_private_course_access(request, course)
    messages.success(request, f"Доступ к курсу «{course.title}» открыт.")
    return redirect("course_detail", slug=course.slug)

# отображение страницы курса
def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.prefetch_related(
            "modules__lessons__attachments",
            "modules__lessons__quiz",
        ),
        slug=slug,
        is_published=True,
    )

    if course.is_private and not _can_access_private_course(request, course):
        messages.error(request, "Этот курс приватный. Сначала введите код и пароль на странице каталога.")
        return redirect("course_list")

    is_enrolled = False
    completed_lesson_ids = []
    completed_quiz_ids = []
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

        if is_enrolled:
            completed_lesson_ids = list(
                LessonProgress.objects.filter(
                    user=request.user,
                    lesson__module__course=course,
                    is_completed=True,
                ).values_list("lesson_id", flat=True)
            )

            completed_quiz_ids = list(
                QuizAttempt.objects.filter(
                    user=request.user,
                    quiz__lesson__module__course=course,
                ).values_list("quiz_id", flat=True).distinct()
            )

    return render(
        request,
        "courses/course_detail.html",
        {
            "course": course,
            "is_enrolled": is_enrolled,
            "private_access_granted": _can_access_private_course(request, course),
            "completed_lesson_ids": completed_lesson_ids,
            "completed_quiz_ids": completed_quiz_ids,
        },
    )

# запись авторизованного пользователя на курс, а для приватного курса сохранение выданного доступ.
@require_POST
@login_required
def enroll(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)

    if course.is_private and not _can_access_private_course(request, course):
        messages.error(request, "Сначала откройте приватный курс по коду и паролю.")
        return redirect("course_list")

    Enrollment.objects.get_or_create(user=request.user, course=course)
    if course.is_private:
        _grant_private_course_access(request, course)
    return redirect("course_detail", slug=course.slug)

# проверка доступа к уроку
def _require_access(request, lesson: Lesson):
    course = lesson.module.course
    if not course.is_published:
        raise Http404
    if not request.user.is_authenticated:
        raise Http404
    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        raise Http404

# отмечает урок как завершённый
@require_POST
@login_required
def complete_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("module__course"), id=lesson_id)
    _require_access(request, lesson)

    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    if not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save()
    return redirect("lesson_detail", lesson_id=lesson.id)


# вывод ошибки 404, если курс не принадлежит пользователю
def _owned_course_or_404(user, course_id: int) -> Course:
    return get_object_or_404(Course, id=course_id, owner=user)

# отображение личного кабинета пользователя
@login_required
def me_dashboard(request):
    # курсы, которые я прохожу
    learning = (
        Enrollment.objects
        .filter(user=request.user)
        .select_related("course")
        .order_by("-created_at")
    )
    # курсы, которые я создал
    my_courses = Course.objects.filter(owner=request.user).order_by("-created_at")

    return render(request, "me/dashboard.html", {
        "learning": learning,
        "my_courses": my_courses,
    })

# создание нового курса
@login_required
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.owner = request.user
            course.save()
            return redirect("course_edit", course_id=course.id)
    else:
        form = CourseForm()
    return render(request, "me/course_form.html", {"form": form, "mode": "create"})

# редактирование курса
@login_required
def course_edit(request, course_id):
    course = get_object_or_404(Course, pk=course_id, owner=request.user)
    modules = course.modules.all().order_by("order")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete_avatar":
            if course.avatar:
                course.avatar.delete(save=False)
            course.avatar = ""
            course.save(update_fields=["avatar"])
            messages.success(request, "Аватар курса удалён.")
            return redirect("course_edit", course_id=course.pk)

        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Курс обновлён.")
            return redirect("course_edit", course_id=course.pk)
    else:
        form = CourseForm(instance=course)

    return render(request, "me/course_edit.html", {
        "course": course,
        "form": form,
        "modules": modules,
    })

# добавление нового модуля в курс
@login_required
def module_add(request, course_id):
    course = _owned_course_or_404(request.user, course_id)

    if request.method == "POST":
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course

            # автоматический порядок
            max_order = course.modules.aggregate(Max("order"))["order__max"] or 0
            module.order = max_order + 1

            module.save()
            return redirect("course_edit", course_id=course.id)
    else:
        form = ModuleForm()

    return render(request, "me/module_form.html", {
        "form": form,
        "course": course
    })

# добавление нового урока
@login_required
def lesson_add(request, module_id):
    module = get_object_or_404(Module.objects.select_related("course"), id=module_id)
    if module.course.owner_id != request.user.id:
        raise Http404

    if request.method == "POST":
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.save()
            return redirect("course_edit", course_id=module.course.id)
    else:
        form = LessonForm()

    return render(request, "me/lesson_form.html", {"form": form, "module": module})

# добавление нового файла к уроку
@login_required
def attachment_add(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("module__course"), id=lesson_id)
    if lesson.module.course.owner_id != request.user.id:
        raise Http404

    if request.method == "POST":
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            att = form.save(commit=False)
            att.lesson = lesson
            att.save()
            return redirect("course_edit", course_id=lesson.module.course.id)
    else:
        form = AttachmentForm()

    return render(request, "me/attachment_form.html", {"form": form, "lesson": lesson})

# управление блоками урока
@login_required
def lesson_blocks_manage(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__owner=request.user)

    if request.method == "POST":
        form = LessonBlockForm(request.POST, request.FILES)
        if form.is_valid():
            block = form.save(commit=False)
            block.lesson = lesson
            block.save()
            messages.success(request, "Блок добавлен.")
            return redirect("lesson_blocks_manage", lesson_id=lesson.id)
    else:
        # order по умолчанию = следующий
        next_order = (lesson.blocks.aggregate(Max("order"))["order__max"] or 0) + 1
        form = LessonBlockForm(initial={"order": next_order})

    return render(request, "courses/lesson_blocks_manage.html", {
        "lesson": lesson,
        "blocks": lesson.blocks.all(),
        "form": form,
    })

# редактирование блоков урока
@login_required
def lesson_block_edit(request, block_id):
    block = get_object_or_404(LessonBlock, id=block_id, lesson__module__course__owner=request.user)

    if request.method == "POST":
        form = LessonBlockForm(request.POST, request.FILES, instance=block)
        if form.is_valid():
            form.save()
            messages.success(request, "Блок обновлён.")
            # Подстраховка: при странных данных lesson_id может оказаться пустым.
            lesson_id = block.lesson_id or (block.lesson.id if getattr(block, "lesson", None) else None)
            if lesson_id:
                return redirect("lesson_blocks_manage", lesson_id=lesson_id)
            return redirect("my_courses")
    else:
        form = LessonBlockForm(instance=block)

    return render(request, "courses/lesson_block_edit.html", {"lesson_block": block, "form": form})

# удаление блока
@login_required
def lesson_block_delete(request, block_id):
    block = get_object_or_404(LessonBlock, id=block_id, lesson__module__course__owner=request.user)

    if request.method == "POST":
        lesson_id = block.lesson_id
        block.delete()
        messages.success(request, "Блок удалён.")
        return redirect("lesson_blocks_manage", lesson_id=lesson_id)

    return render(request, "courses/lesson_block_delete.html", {"block": block})

# создание урока с блоками
@login_required
def lesson_create_with_blocks(request, module_id):
    module = get_object_or_404(Module, id=module_id)

    next_lesson_order = (module.lessons.aggregate(max_order=Max("order"))["max_order"] or 0) + 1

    if request.method == "POST":
        lesson_form = LessonForm(request.POST)
        formset = LessonBlockFormSet(request.POST, request.FILES)

        if lesson_form.is_valid() and formset.is_valid():
            lesson = lesson_form.save(commit=False)
            lesson.module = module
            lesson.order = next_lesson_order
            lesson.save()

            formset.instance = lesson
            formset.save()

            return redirect("course_edit", course_id=module.course.id)
    else:
        lesson_form = LessonForm()
        formset = LessonBlockFormSet()

    return render(request, "me/lesson_create_with_blocks.html", {
        "module": module,
        "lesson_form": lesson_form,
        "formset": formset,
        "next_lesson_order": next_lesson_order,
    })


# создание или редактирование теста у урока
@login_required
def quiz_manage(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__owner=request.user)
    quiz, _ = Quiz.objects.get_or_create(lesson=lesson)

    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "Тест сохранён.")
            return redirect("quiz_manage", lesson_id=lesson.id)
    else:
        form = QuizForm(instance=quiz)

    return render(request, "me/quiz_manage.html", {"lesson": lesson, "quiz": quiz, "form": form, "questions": quiz.questions.all()})

# создание вопроса для теста
@login_required
def question_create(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, lesson__module__course__owner=request.user)

    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.quiz = quiz

            if q.type != Question.TEXT:
                q.correct_text = ""
                q.text_case_sensitive = False

            q.save()
            messages.success(request, "Вопрос создан. Теперь добавь варианты или пары.")
            return redirect("question_edit", question_id=q.id)
    else:
        next_order = (
            quiz.questions
            .order_by("-order")
            .values_list("order", flat=True)
            .first() or 0
        ) + 1

        form = QuestionForm(initial={
            "order": next_order,
            "points": 1,
            "type": Question.SINGLE
        })

    return render(request, "me/question_form.html", {"quiz": quiz, "form": form})

# редактирование вопроса теста
@login_required
def question_edit(request, question_id):
    q = get_object_or_404(Question, id=question_id, quiz__lesson__module__course__owner=request.user)

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=q)
        choice_fs = ChoiceFormSet(request.POST, instance=q, prefix="choices")
        pair_fs = MatchPairFormSet(request.POST, instance=q, prefix="pairs")

        ok = form.is_valid()
        new_type = form.cleaned_data["type"] if ok else q.type

        if ok and new_type in (Question.SINGLE, Question.MULTI):
            ok = choice_fs.is_valid()
        elif ok and new_type == Question.MATCH:
            ok = pair_fs.is_valid()

        if ok:
            obj = form.save(commit=False)

            if new_type != Question.TEXT:
                obj.correct_text = ""
                obj.text_case_sensitive = False

            obj.save()

            if new_type in (Question.SINGLE, Question.MULTI):
                pair_fs = MatchPairFormSet(instance=obj, prefix="pairs")
                choice_fs.save()
            elif new_type == Question.MATCH:
                choice_fs = ChoiceFormSet(instance=obj, prefix="choices")
                pair_fs.save()

            messages.success(request, "Вопрос сохранён.")
            return redirect("quiz_manage", lesson_id=obj.quiz.lesson_id)
    else:
        form = QuestionForm(instance=q)
        choice_fs = ChoiceFormSet(instance=q, prefix="choices")
        pair_fs = MatchPairFormSet(instance=q, prefix="pairs")

    return render(request, "me/question_edit.html", {
        "q": q,
        "form": form,
        "choice_formset": choice_fs,
        "pair_formset": pair_fs,
    })

# удаление вопроса из теста
@login_required
def question_delete(request, question_id):
    q = get_object_or_404(Question, id=question_id, quiz__lesson__module__course__owner=request.user)
    if request.method == "POST":
        lesson_id = q.quiz.lesson_id
        q.delete()
        messages.success(request, "Вопрос удалён.")
        return redirect("quiz_manage", lesson_id=lesson_id)
    return render(request, "me/question_delete.html", {"q": q})


#прохождение теста урока для обучающего
@login_required
def quiz_take(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    quiz = getattr(lesson, "quiz", None)
    if not quiz or not quiz.is_published:
        messages.error(request, "Тест недоступен.")
        return redirect("lesson_detail", lesson_id=lesson.id)

    questions = quiz.questions.prefetch_related("choices", "pairs")

    if request.method == "POST":
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            max_score=sum(q.points for q in questions),
        )

        score = 0

        for q in questions:
            ans = Answer.objects.create(attempt=attempt, question=q)

            # SINGLE
            if q.type == Question.SINGLE:
                cid = request.POST.get(f"q{q.id}")
                if cid:
                    try:
                        c = q.choices.get(id=int(cid))
                        ans.selected_choices.add(c)
                        if c.is_correct:
                            ans.is_correct = True
                            ans.earned_points = q.points
                            score += q.points
                    except (Choice.DoesNotExist, ValueError):
                        pass

            # MULTI
            elif q.type == Question.MULTI:
                cids = request.POST.getlist(f"q{q.id}")
                selected = list(q.choices.filter(id__in=cids))
                if selected:
                    ans.selected_choices.add(*selected)
                correct_ids = set(q.choices.filter(is_correct=True).values_list("id", flat=True))
                selected_ids = set(c.id for c in selected)
                if correct_ids and selected_ids == correct_ids:
                    ans.is_correct = True
                    ans.earned_points = q.points
                    score += q.points

            # TEXT
            elif q.type == Question.TEXT:
                val = (request.POST.get(f"q{q.id}") or "").strip()
                ans.text_value = val
                if val:
                    a = val if q.text_case_sensitive else val.lower()
                    b = q.correct_text.strip() if q.text_case_sensitive else q.correct_text.strip().lower()
                    if b and a == b:
                        ans.is_correct = True
                        ans.earned_points = q.points
                        score += q.points

            # MATCH
            elif q.type == Question.MATCH:
                # для каждой пары left -> выбранный right_text
                mapping = {}
                pairs = list(q.pairs.all())
                correct = True
                for idx, p in enumerate(pairs):
                    chosen = (request.POST.get(f"q{q.id}_p{p.id}") or "").strip()
                    mapping[str(p.id)] = chosen
                    if chosen != p.right_text:
                        correct = False
                ans.match_map = mapping
                if pairs and correct:
                    ans.is_correct = True
                    ans.earned_points = q.points
                    score += q.points

            ans.save()

        now = timezone.now()

        attempt.score = score
        attempt.is_late = bool(quiz.deadline and now > quiz.deadline)
        attempt.save()
        answers = (
            attempt.answers
            .select_related("question")
            .prefetch_related("selected_choices", "question__choices", "question__pairs")
        )

        return render(request, "courses/quiz_result.html", {
            "lesson": lesson,
            "quiz": quiz,
            "attempt": attempt,
            "answers": answers,
        })
    
    match_options = {}

    for q in questions:
        if q.type == Question.MATCH:
            rights = list(q.pairs.values_list("right_text", flat=True))
            # убираем дубликаты, но сохраняем значения
            rights = list(dict.fromkeys(rights))
            random.shuffle(rights)
            match_options[q.id] = rights

    return render(request, "courses/quiz_take.html", {
        "lesson": lesson,
        "quiz": quiz,
        "questions": questions,
        "match_options": match_options,
    })

# проверка доступа к тесту (дедлайн)
def get_quiz_access_state(quiz):
    now = timezone.now()

    is_not_opened = bool(quiz.available_from and now < quiz.available_from)
    is_deadline_passed = bool(quiz.deadline and now > quiz.deadline)

    return {
        "now": now,
        "is_not_opened": is_not_opened,
        "is_deadline_passed": is_deadline_passed,
        "can_start": not is_not_opened,  # после дедлайна старт всё ещё разрешён
    }

# отображение страницы урока
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related("module__course", "quiz").prefetch_related(
            "blocks",
            "attachments",
        ),
        id=lesson_id,
    )

    _require_access(request, lesson)

    progress, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

    course = lesson.module.course

    lessons_qs = (
        Lesson.objects
        .filter(module__course=course)
        .select_related("module")
        .order_by("module__order", "order", "id")
    )

    lesson_ids = list(lessons_qs.values_list("id", flat=True))
    prev_lesson = None
    next_lesson = None

    try:
        idx = lesson_ids.index(lesson.id)
        if idx > 0:
            prev_lesson = lessons_qs.get(id=lesson_ids[idx - 1])
        if idx < len(lesson_ids) - 1:
            next_lesson = lessons_qs.get(id=lesson_ids[idx + 1])
    except ValueError:
        pass

    quiz = getattr(lesson, "quiz", None)
    quiz_access = get_quiz_access_state(quiz) if quiz else None

    context = {
        "lesson": lesson,
        "quiz": quiz,
        "quiz_access": quiz_access,
        "prev_lesson": prev_lesson,
        "next_lesson": next_lesson,
        "progress": progress,
    }

    return render(request, "courses/lesson_detail.html", context)

# просмотр списка попыток прохождения теста
@login_required
def quiz_attempts(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    quiz = getattr(lesson, "quiz", None)

    if not quiz:
        raise Http404

    attempts = list(
        QuizAttempt.objects.filter(
            quiz=quiz,
            user=request.user
        ).order_by("-created_at")
    )

    def get_percent(a):
        return round((a.score / a.max_score) * 100) if a and a.max_score else 0

    def get_level(percent):
        if percent < 50:
            return "low"
        elif percent < 80:
            return "mid"
        return "high"

    for attempt in attempts:
        attempt.percent_value = get_percent(attempt)
        attempt.percent_level = get_level(attempt.percent_value)

    best_attempt = max(
        attempts,
        key=lambda a: (a.score or 0, a.max_score or 0, a.created_at),
        default=None
    )

    best_percent = get_percent(best_attempt)
    best_percent_level = get_level(best_percent)

    return render(request, "courses/quiz_attempts.html", {
        "lesson": lesson,
        "quiz": quiz,
        "attempts": attempts,
        "best_attempt": best_attempt,
        "best_percent": best_percent,
        "best_percent_level": best_percent_level,
    })

# отображение подробного результата попытки теста
@login_required
def quiz_attempt_detail(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related(
            "quiz__lesson",
            "user",
            "user__profile",
        ).prefetch_related(
            "answers__selected_choices",
            "answers__question__choices",
            "answers__question__pairs"
        ),
        id=attempt_id,
        user=request.user
    )

    answers = attempt.answers.all().select_related("question").order_by("question__order", "id")

    if attempt.max_score:
        percent = round((attempt.score / attempt.max_score) * 100)
    else:
        percent = 0

    if percent < 50:
        percent_level = "low"
    elif percent < 80:
        percent_level = "mid"
    else:
        percent_level = "high"

    return render(request, "courses/quiz_result.html", {
        "lesson": attempt.quiz.lesson,
        "quiz": attempt.quiz,
        "attempt": attempt,
        "answers": answers,
        "percent": percent,
        "percent_level": percent_level,
    })

# представление лучшего результата ученика по тесту
@login_required
def quiz_students_results(request, lesson_id):
    lesson = get_object_or_404(
        Lesson.objects.select_related("module__course"),
        id=lesson_id,
        module__course__owner=request.user,
    )

    quiz = getattr(lesson, "quiz", None)
    if not quiz:
        raise Http404

    attempts = list(
        QuizAttempt.objects
        .filter(quiz=quiz)
        .select_related("user", "user__profile")
        .order_by("user_id", "-score", "-max_score", "-created_at")
        .distinct("user_id")
    )

    attempts = sorted(
        attempts,
        key=lambda a: (
            -(a.score or 0),
            -(a.max_score or 0),
            -a.created_at.timestamp() if a.created_at else 0,
        )
    )

    for attempt in attempts:
        if attempt.max_score:
            percent_value = round((attempt.score / attempt.max_score) * 100)
        else:
            percent_value = 0

        if percent_value < 50:
            percent_level = "low"
        elif percent_value < 80:
            percent_level = "mid"
        else:
            percent_level = "high"

        attempt.percent_value = percent_value
        attempt.percent_level = percent_level

    return render(request, "me/quiz_students_results.html", {
        "lesson": lesson,
        "quiz": quiz,
        "attempts": attempts,
    })

# представление подробного отчета по лучшей попытке обучающегося преподавателю
@login_required
def quiz_student_attempt_detail(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related(
            "quiz__lesson__module__course",
            "user",
            "user__profile",
        ).prefetch_related(
            "answers__selected_choices",
            "answers__question__choices",
            "answers__question__pairs",
        ),
        id=attempt_id,
        quiz__lesson__module__course__owner=request.user,
    )

    answers = attempt.answers.all().select_related("question").order_by("question__order", "id")

    if attempt.max_score:
        percent = round((attempt.score / attempt.max_score) * 100)
    else:
        percent = 0

    if percent < 50:
        percent_level = "low"
    elif percent < 80:
        percent_level = "mid"
    else:
        percent_level = "high"

    return render(request, "me/quiz_student_attempt_detail.html", {
        "attempt": attempt,
        "lesson": attempt.quiz.lesson,
        "quiz": attempt.quiz,
        "answers": answers,
        "percent": percent,
        "percent_level": percent_level,
    })

# представление общего прогресса обучающих по курсу
@login_required
def course_students_progress(request, slug):
    course = get_object_or_404(
        Course.objects.select_related("owner"),
        slug=slug,
        owner=request.user,
    )

    enrollments = (
        Enrollment.objects
        .filter(course=course)
        .select_related("user")
        .order_by("user__username")
    )

    lessons = Lesson.objects.filter(module__course=course)
    total_lessons = lessons.count()
    lesson_ids = list(lessons.values_list("id", flat=True))

    quiz_lesson_ids = list(
        Lesson.objects.filter(module__course=course, quiz__isnull=False)
        .values_list("id", flat=True)
    )
    total_tests = len(quiz_lesson_ids)

    students_progress = []

    for enrollment in enrollments:
        user = enrollment.user

        lessons_done = LessonProgress.objects.filter(
            user=user,
            lesson_id__in=lesson_ids,
            is_completed=True,
        ).count()

        tests_done = QuizAttempt.objects.filter(
            user=user,
            quiz__lesson_id__in=quiz_lesson_ids,
        ).values("quiz_id").distinct().count()

        total_items = total_lessons + total_tests
        done_items = lessons_done + tests_done
        percent = round((done_items / total_items) * 100) if total_items else 0

        students_progress.append({
            "user": user,
            "enrollment": enrollment,
            "lessons_done": lessons_done,
            "lessons_total": total_lessons,
            "tests_done": tests_done,
            "tests_total": total_tests,
            "percent": percent,
        })

    students_progress.sort(key=lambda x: (-x["percent"], x["user"].username.lower()))

    return render(request, "me/course_students_progress.html", {
        "course": course,
        "students_progress": students_progress,
        "total_lessons": total_lessons,
        "total_tests": total_tests,
        "enrollments": enrollments,
        "enrollments_count": enrollments.count(),
    })

# удаление урока из можуля
@login_required
def lesson_delete(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    # проверка, что курс действительно принадлежит текущему пользователю
    course = _owned_course_or_404(request.user, lesson.module.course.id)

    if request.method == "POST":
        module = lesson.module
        course_id = course.id

        lesson.delete()
        # перенумерация уроков в модуле после удаления
        lessons = module.lessons.order_by("order", "id")
        for index, item in enumerate(lessons, start=1):
            if item.order != index:
                item.order = index
                item.save(update_fields=["order"])

        messages.success(request, "Урок удалён.")
        return redirect("course_edit", course_id=course_id)

    return redirect("course_edit", course_id=course.id)

# удаление курса
@login_required
def course_delete(request, course_id):
    course = _owned_course_or_404(request.user, course_id)

    if request.method == "POST":
        course.delete()
        messages.success(request, "Курс удалён.")
        return redirect("me_dashboard")

    return redirect("course_edit", course_id=course.id)

# перемещение уроков ввер и вниз внутри модуля
def lesson_move(request, lesson_id, direction):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = _owned_course_or_404(request.user, lesson.module.course.id)
    module = lesson.module

    lessons = list(module.lessons.order_by("order", "id"))
    ids = [x.id for x in lessons]

    try:
        index = ids.index(lesson.id)
    except ValueError:
        messages.error(request, "Урок не найден.")
        return redirect("course_edit", course_id=course.id)

    if direction == "up" and index > 0:
        other = lessons[index - 1]
    elif direction == "down" and index < len(lessons) - 1:
        other = lessons[index + 1]
    else:
        return redirect("course_edit", course_id=course.id)

    lesson_order = lesson.order
    other_order = other.order

    temp_order = 999999

    # 1. освобождаем место
    lesson.order = temp_order
    lesson.save(update_fields=["order"])

    # 2. двигаем соседний
    other.order = lesson_order
    other.save(update_fields=["order"])

    # 3. ставим текущий на место соседнего
    lesson.order = other_order
    lesson.save(update_fields=["order"])

    return redirect("course_edit", course_id=course.id)