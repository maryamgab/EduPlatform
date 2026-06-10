from django import template
from courses.models import Enrollment, Lesson, Quiz, QuizAttempt, LessonProgress

register = template.Library()


@register.simple_tag(takes_context=True)
def course_progress(context, course):
    request = context.get("request")
    user = getattr(request, "user", None)

    lessons_total = Lesson.objects.filter(module__course=course).count()
    tests_total = Quiz.objects.filter(
        lesson__module__course=course,
        is_published=True,
    ).count()

    lessons_done = 0
    tests_done = 0
    is_enrolled = False

    if user and user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(user=user, course=course).exists()

        if is_enrolled:
            lessons_done = LessonProgress.objects.filter(
                user=user,
                lesson__module__course=course,
                is_completed=True,
            ).count()

            tests_done = (
                QuizAttempt.objects.filter(user=user, quiz__lesson__module__course=course)
                .values("quiz_id")
                .distinct()
                .count()
            )

    total = lessons_total + tests_total
    done = lessons_done + tests_done
    percent = round(done * 100 / total) if total else 0

    return {
        "percent": percent,
        "done": done,
        "total": total,
        "lessons_done": lessons_done,
        "lessons_total": lessons_total,
        "tests_done": tests_done,
        "tests_total": tests_total,
        "is_enrolled": is_enrolled,
    }
