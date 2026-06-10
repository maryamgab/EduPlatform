import json
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, Enrollment, Lesson, LessonProgress, Quiz, QuizAttempt, Question
from .models import Profile, TelegramNotificationLog

logger = logging.getLogger(__name__)

BUTTON_COURSES = "📚 Мои курсы"
BUTTON_DEADLINES = "⏰ Дедлайны"
BUTTON_HELP = "❓ Помощь"
BUTTON_UNLINK = "🔌 Отвязать Telegram"
LINK_CODE_RE = re.compile(r"^[A-Z0-9]{6,32}$")


def telegram_is_configured() -> bool:
    return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip())


def _bot_api_url(method: str) -> str:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "").strip()
    return f"https://api.telegram.org/bot{token}/{method}"


def telegram_api_request(method: str, payload: Optional[dict] = None, timeout: int = 30):
    if not telegram_is_configured():
        logger.warning("Telegram bot token is not configured")
        return None

    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        _bot_api_url(method),
        data=data,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=max(timeout + 10, 20)) as response:
            raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            if not parsed.get("ok"):
                logger.warning("Telegram API %s returned non-ok payload: %s", method, parsed)
                return None
            return parsed.get("result")
    except urllib.error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8")
        except Exception:
            details = str(exc)
        logger.warning("Telegram API HTTP error on %s: %s", method, details)
    except Exception:
        logger.exception("Telegram API request failed for %s", method)
    return None


def get_main_keyboard(is_linked: bool = True) -> dict:
    keyboard = [
        [{"text": BUTTON_COURSES}, {"text": BUTTON_DEADLINES}],
        [{"text": BUTTON_HELP}],
    ]
    if is_linked:
        keyboard.append([{"text": BUTTON_UNLINK}])
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def send_telegram_message(chat_id: str, text: str, reply_markup: Optional[dict] = None) -> bool:
    if not chat_id:
        return False

    payload = {
        "chat_id": str(chat_id),
        "text": (text or "")[:4096],
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    result = telegram_api_request("sendMessage", payload=payload)
    return bool(result)


def fetch_updates(offset: int = 0, timeout: Optional[int] = None):
    poll_timeout = timeout if timeout is not None else int(getattr(settings, "TELEGRAM_BOT_POLL_TIMEOUT", 30) or 30)
    return telegram_api_request(
        "getUpdates",
        payload={
            "offset": offset,
            "timeout": poll_timeout,
            "allowed_updates": ["message"],
        },
        timeout=poll_timeout,
    ) or []


def _site_url(path: str = "") -> str:
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    if not base:
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


def _course_tag(course: Course) -> str:
    parts = []
    parts.append("приватный" if course.is_private else "публичный")
    parts.append("опубликован" if course.is_published else "черновик")
    return ", ".join(parts)


def _course_progress_for_user(user, course: Course) -> dict:
    lessons_total = Lesson.objects.filter(module__course=course).count()
    tests_total = Quiz.objects.filter(lesson__module__course=course, is_published=True).count()

    lessons_done = LessonProgress.objects.filter(
        user=user,
        lesson__module__course=course,
        is_completed=True,
    ).count()
    tests_done = (
        QuizAttempt.objects
        .filter(user=user, quiz__lesson__module__course=course)
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
    }


def _format_learning_course_lines(user, courses) -> list[str]:
    lines = []
    for course in courses:
        progress = _course_progress_for_user(user, course)
        course_url = _site_url(reverse("course_detail", kwargs={"slug": course.slug})) if course.is_published else ""
        if progress["total"]:
            line = (
                f"• {course.title} — {progress['percent']}% "
                f"({progress['done']}/{progress['total']}) [{_course_tag(course)}]"
            )
        else:
            line = f"• {course.title} — 0% [{_course_tag(course)}]"
        if course_url:
            line += f"\n  {course_url}"
        lines.append(line)
    return lines


def _format_course_lines(courses) -> list[str]:
    lines = []
    for course in courses:
        course_url = _site_url(reverse("course_detail", kwargs={"slug": course.slug})) if course.is_published else ""
        line = f"• {course.title} ({_course_tag(course)})"
        if course_url:
            line += f"\n  {course_url}"
        lines.append(line)
    return lines


def get_user_courses_text(user, limit: int = 10) -> str:
    learning_qs = Course.objects.filter(enrollments__user=user).distinct().order_by("title")
    created_qs = Course.objects.filter(owner=user).distinct().order_by("title")
    learning_total = learning_qs.count()
    created_total = created_qs.count()
    learning_courses = list(learning_qs[:limit])
    created_courses = list(created_qs[:limit])

    lines = ["📚 Ваши курсы"]
    lines.append("")
    lines.append(f"Проходите сейчас: {learning_total}")
    if learning_courses:
        lines.extend(_format_learning_course_lines(user, learning_courses))
    else:
        lines.append("• Пока нет курсов, на которые вы записаны.")

    lines.append("")
    lines.append(f"Созданные вами: {created_total}")
    if created_courses:
        lines.extend(_format_course_lines(created_courses))
    else:
        lines.append("• Пока нет созданных вами курсов.")

    if learning_total > limit or created_total > limit:
        lines.append("")
        lines.append("Показана только часть списка.")

    return "\n".join(lines)


def get_user_deadlines_text(user, limit: int = 5) -> str:
    quizzes = list(
        Quiz.objects.filter(
            lesson__module__course__enrollments__user=user,
            lesson__module__course__is_published=True,
            is_published=True,
            deadline__isnull=False,
            deadline__gte=timezone.now(),
        )
        .exclude(attempts__user=user)
        .select_related("lesson__module__course")
        .order_by("deadline")
        .distinct()[:limit]
    )

    if not quizzes:
        return "⏰ Ближайших дедлайнов сейчас нет."

    lines = ["⏰ Ближайшие дедлайны", ""]
    for quiz in quizzes:
        course = quiz.lesson.module.course
        lines.append(
            f"• {course.title}\n"
            f"  Тест: {quiz.title}\n"
            f"  Урок: {quiz.lesson.title}\n"
            f"  До {timezone.localtime(quiz.deadline).strftime('%d.%m.%Y %H:%M')}"
        )
    return "\n".join(lines)


def get_help_text(is_linked: bool = False) -> str:
    profile_url = _site_url(reverse("profile_page"))
    lines = [
        "🤖 Команды бота:",
        "/start — открыть главное меню",
        "/courses — показать ваши курсы",
        "/deadlines — ближайшие дедлайны",
        "/unlink — отвязать Telegram",
        "/help — помощь",
        "",
    ]
    if is_linked:
        lines.append("Аккаунт уже привязан. Используйте кнопки меню или команды выше.")
    else:
        lines.append(
            "Чтобы привязать аккаунт, откройте профиль на сайте, сгенерируйте код и отправьте команду /start CODE."
        )
        if profile_url:
            lines.append(profile_url)
    return "\n".join(lines)


def connect_profile_by_code(code: str, chat_id: str, username: str = ""):
    normalized_code = (code or "").strip().upper()
    if not normalized_code:
        return None, "Не вижу код привязки. Откройте профиль на сайте и сгенерируйте новый код."

    profile = Profile.objects.filter(telegram_link_code=normalized_code).select_related("user").first()
    if not profile:
        return None, "Код привязки не найден или уже использован. Сгенерируйте новый код в профиле."

    now = timezone.now()
    Profile.objects.filter(telegram_chat_id=str(chat_id)).exclude(pk=profile.pk).update(
        telegram_chat_id="",
        telegram_username="",
        telegram_connected_at=None,
        telegram_link_code="",
        telegram_link_code_created_at=None,
    )

    profile.telegram_chat_id = str(chat_id)
    profile.telegram_username = (username or "").lstrip("@")
    profile.telegram_connected_at = now
    profile.telegram_link_code = ""
    profile.telegram_link_code_created_at = None
    profile.save(
        update_fields=[
            "telegram_chat_id",
            "telegram_username",
            "telegram_connected_at",
            "telegram_link_code",
            "telegram_link_code_created_at",
        ]
    )

    message = (
        f"✅ Telegram успешно привязан к аккаунту {profile.user.username}.\n\n"
        "Теперь вы можете получать уведомления о новых уроках, тестах и дедлайнах."
    )
    return profile, message


def disconnect_profile_by_chat(chat_id: str):
    profile = Profile.objects.filter(telegram_chat_id=str(chat_id)).select_related("user").first()
    if not profile:
        return None, "Этот Telegram пока не привязан к аккаунту."

    profile.clear_telegram_connection()
    profile.save(
        update_fields=[
            "telegram_chat_id",
            "telegram_username",
            "telegram_connected_at",
            "telegram_link_code",
            "telegram_link_code_created_at",
        ]
    )
    return profile, "🔌 Telegram отвязан от вашего аккаунта."


def get_profile_by_chat(chat_id: str):
    return Profile.objects.filter(telegram_chat_id=str(chat_id)).select_related("user").first()


def _notification_allowed(profile: Profile, attr_name: str) -> bool:
    return bool(
        profile.telegram_chat_id
        and profile.telegram_notifications_enabled
        and getattr(profile, attr_name, False)
    )


def _send_once(profile: Profile, unique_key: str, kind: str, text: str) -> bool:
    try:
        TelegramNotificationLog.objects.create(profile=profile, unique_key=unique_key, kind=kind)
    except IntegrityError:
        return False

    ok = send_telegram_message(profile.telegram_chat_id, text, reply_markup=get_main_keyboard(is_linked=True))
    if not ok:
        TelegramNotificationLog.objects.filter(profile=profile, unique_key=unique_key).delete()
        return False
    return True


def notify_new_lesson(lesson_id: int):
    lesson = Lesson.objects.select_related("module__course").filter(pk=lesson_id).first()
    if not lesson:
        return 0

    course = lesson.module.course
    if not course.is_published:
        return 0

    profiles = (
        Profile.objects.filter(user__enrollments__course=course)
        .select_related("user")
        .distinct()
    )

    text = (
        f"📘 В курсе «{course.title}» появился новый урок.\n\n"
        f"Урок: {lesson.title}\n"
        f"Модуль: {lesson.module.title}"
    )
    course_url = _site_url(reverse("course_detail", kwargs={"slug": course.slug}))
    if course_url:
        text += f"\n\nОткрыть курс: {course_url}"

    sent = 0
    unique_key = f"new_lesson:{lesson.pk}"
    for profile in profiles:
        if _notification_allowed(profile, "telegram_notify_new_lessons"):
            sent += int(_send_once(profile, unique_key, "new_lesson", text))
    return sent


def notify_new_quiz_if_ready(quiz_id: int):
    quiz = Quiz.objects.select_related("lesson__module__course").filter(pk=quiz_id).first()
    if not quiz or not quiz.is_published:
        return 0

    course = quiz.lesson.module.course
    if not course.is_published:
        return 0

    if not Question.objects.filter(quiz=quiz).exists():
        return 0

    profiles = (
        Profile.objects.filter(user__enrollments__course=course)
        .select_related("user")
        .distinct()
    )

    text = (
        f"📝 В курсе «{course.title}» появился новый тест.\n\n"
        f"Тест: {quiz.title}\n"
        f"Урок: {quiz.lesson.title}"
    )
    if quiz.deadline:
        text += f"\nДедлайн: {timezone.localtime(quiz.deadline).strftime('%d.%m.%Y %H:%M')}"

    lesson_url = _site_url(reverse("lesson_detail", kwargs={"lesson_id": quiz.lesson_id}))
    if lesson_url:
        text += f"\n\nОткрыть урок: {lesson_url}"

    sent = 0
    unique_key = f"new_quiz:{quiz.pk}"
    for profile in profiles:
        if _notification_allowed(profile, "telegram_notify_new_quizzes"):
            sent += int(_send_once(profile, unique_key, "new_quiz", text))
    return sent


def _deadline_window_key(quiz: Quiz, now):
    delta = quiz.deadline - now
    if delta <= timedelta(hours=3):
        return "3h"
    if delta <= timedelta(hours=24):
        return "24h"
    if delta <= timedelta(days=3):
        return "3d"
    return ""


def _deadline_label(window_key: str) -> str:
    return {
        "3h": "меньше 3 часов",
        "24h": "меньше 24 часов",
        "3d": "меньше 3 дней",
    }.get(window_key, "скоро")


def send_upcoming_deadline_notifications(now=None):
    now = now or timezone.now()
    quizzes = (
        Quiz.objects.filter(
            is_published=True,
            lesson__module__course__is_published=True,
            deadline__isnull=False,
            deadline__gt=now,
            deadline__lte=now + timedelta(days=3),
        )
        .select_related("lesson__module__course")
        .distinct()
        .order_by("deadline")
    )

    sent = 0
    for quiz in quizzes:
        window_key = _deadline_window_key(quiz, now)
        if not window_key:
            continue

        course = quiz.lesson.module.course
        text = (
            f"⏰ Приближается дедлайн по курсу «{course.title}».\n\n"
            f"Тест: {quiz.title}\n"
            f"Урок: {quiz.lesson.title}\n"
            f"Срок сдачи: {timezone.localtime(quiz.deadline).strftime('%d.%m.%Y %H:%M')}\n"
            f"До дедлайна: {_deadline_label(window_key)}"
        )
        lesson_url = _site_url(reverse("lesson_detail", kwargs={"lesson_id": quiz.lesson_id}))
        if lesson_url:
            text += f"\n\nОткрыть урок: {lesson_url}"

        profiles = (
            Profile.objects.filter(user__enrollments__course=course)
            .exclude(user__quiz_attempts__quiz=quiz)
            .select_related("user")
            .distinct()
        )
        unique_key = f"deadline:{quiz.pk}:{window_key}"
        for profile in profiles:
            if _notification_allowed(profile, "telegram_notify_deadlines"):
                sent += int(_send_once(profile, unique_key, "deadline", text))
    return sent


def handle_telegram_text_message(chat_id: str, text: str, username: str = "") -> str:
    text = (text or "").strip()
    command = text.split(maxsplit=1)[0].lower() if text else ""
    args = text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) > 1 else ""
    profile = get_profile_by_chat(chat_id)

    if command == "/start":
        if args:
            profile, message = connect_profile_by_code(args, chat_id=chat_id, username=username)
            return message + "\n\n" + get_user_courses_text(profile.user) if profile else message
        if profile:
            return (
                f"Привет, {profile.user.username}!\n\n"
                "Я готов присылать уведомления и показывать ваши курсы."
            )
        return (
            "Привет! Я Telegram-бот учебной платформы.\n\n"
            "Чтобы привязать аккаунт, откройте профиль на сайте, сгенерируйте код и отправьте команду /start CODE."
        )

    if command in {"/help", BUTTON_HELP.lower()} or text == BUTTON_HELP:
        return get_help_text(is_linked=bool(profile))

    if command in {"/courses"} or text == BUTTON_COURSES:
        if not profile:
            return get_help_text(is_linked=False)
        return get_user_courses_text(profile.user)

    if command in {"/deadlines"} or text == BUTTON_DEADLINES:
        if not profile:
            return get_help_text(is_linked=False)
        return get_user_deadlines_text(profile.user)

    if command in {"/unlink"} or text == BUTTON_UNLINK:
        _, message = disconnect_profile_by_chat(chat_id)
        return message

    if not profile and LINK_CODE_RE.match(text.upper()):
        linked_profile, message = connect_profile_by_code(text, chat_id=chat_id, username=username)
        if linked_profile:
            return message + "\n\n" + get_user_courses_text(linked_profile.user)
        return message

    if profile:
        return (
            "Не понял команду. Используйте кнопки меню или /help."
        )
    return get_help_text(is_linked=False)


def process_telegram_update(update: dict) -> bool:
    message = update.get("message") or {}
    text = message.get("text")
    if not text:
        return False

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = str(chat.get("id") or "")
    username = (from_user.get("username") or "").strip()
    if not chat_id:
        return False

    profile = get_profile_by_chat(chat_id)
    response_text = handle_telegram_text_message(chat_id=chat_id, text=text, username=username)
    send_telegram_message(chat_id, response_text, reply_markup=get_main_keyboard(is_linked=bool(profile or get_profile_by_chat(chat_id))))
    return True


class PollLoopState:
    def __init__(self):
        self.last_deadline_check_at = timezone.now() - timedelta(minutes=10)

    def maybe_send_deadlines(self):
        if timezone.now() - self.last_deadline_check_at >= timedelta(minutes=5):
            sent = send_upcoming_deadline_notifications()
            self.last_deadline_check_at = timezone.now()
            return sent
        return 0

    def backoff(self, seconds: int = 2):
        time.sleep(seconds)
