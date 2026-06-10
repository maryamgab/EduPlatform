from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from courses.models import Quiz
from .models import Profile
from .profile_forms import ProfileForm, EmailChangeForm, TelegramNotificationsForm
from .telegram import connect_profile_by_code


@login_required
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    profile_form = ProfileForm(instance=profile)
    email_form = EmailChangeForm(request.user, initial={"email": request.user.email})
    password_form = PasswordChangeForm(user=request.user)
    telegram_form = TelegramNotificationsForm(instance=profile)
    upcoming_deadlines = (
        Quiz.objects
        .filter(
            lesson__module__course__enrollments__user=request.user,
            lesson__module__course__is_published=True,
            is_published=True,
            deadline__isnull=False,
            deadline__gte=timezone.now(),
        )
        .exclude(attempts__user=request.user)
        .select_related("lesson", "lesson__module", "lesson__module__course")
        .distinct()
        .order_by("deadline")[:5]
    )

    telegram_bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "").strip("@")
    telegram_bot_link = ""
    if telegram_bot_username and profile.telegram_link_code:
        telegram_bot_link = f"https://t.me/{telegram_bot_username}?start={profile.telegram_link_code}"

    if request.method == "POST":
        action = request.POST.get("action")

        # 1) Обновление профиля
        if action == "profile":
            profile_form = ProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профиль обновлён.")
                return redirect("profile_page")

        # 2) Смена email
        elif action == "email":
            email_form = EmailChangeForm(request.user, request.POST)
            if email_form.is_valid():
                request.user.email = email_form.cleaned_data["email"]
                request.user.save(update_fields=["email"])
                messages.success(request, "Почта изменена.")
                return redirect("profile_page")

        # 3) Смена пароля
        elif action == "password":
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # не разлогинивает
                messages.success(request, "Пароль изменён.")
                return redirect("profile_page")

        elif action == "telegram_generate":
            profile.generate_telegram_link_code()
            profile.save(update_fields=["telegram_link_code", "telegram_link_code_created_at"])
            messages.success(request, "Код привязки Telegram обновлён.")
            return redirect("profile_page")

        elif action == "telegram_notifications":
            telegram_form = TelegramNotificationsForm(request.POST, instance=profile)
            if telegram_form.is_valid():
                telegram_form.save()
                messages.success(request, "Настройки уведомлений Telegram сохранены.")
                return redirect("profile_page")

        elif action == "telegram_disconnect":
            if profile.telegram_is_connected:
                profile.clear_telegram_connection()
                profile.save(update_fields=[
                    "telegram_chat_id",
                    "telegram_username",
                    "telegram_connected_at",
                    "telegram_link_code",
                    "telegram_link_code_created_at",
                ])
                messages.success(request, "Telegram отключён от профиля.")
            else:
                messages.info(request, "Telegram пока не был привязан.")
            return redirect("profile_page")

        else:
            messages.error(request, "Неизвестное действие формы.")

    return render(request, "me/profile_page.html", {
        "profile_form": profile_form,
        "email_form": email_form,
        "password_form": password_form,
        "telegram_form": telegram_form,
        "upcoming_deadlines": upcoming_deadlines,
        "telegram_bot_username": telegram_bot_username,
        "telegram_bot_link": telegram_bot_link,
    })


@csrf_exempt
@require_POST
def telegram_connect_api(request):
    api_secret = (request.POST.get("secret") or "").strip()
    expected_secret = getattr(settings, "TELEGRAM_LINK_SECRET", "").strip()

    if not expected_secret:
        return JsonResponse({"ok": False, "error": "telegram_link_secret_not_configured"}, status=503)

    if api_secret != expected_secret:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    code = (request.POST.get("code") or "").strip().upper()
    chat_id = (request.POST.get("chat_id") or "").strip()
    username = (request.POST.get("username") or "").strip().lstrip("@")

    if not code or not chat_id:
        return JsonResponse({"ok": False, "error": "code_and_chat_id_required"}, status=400)

    profile = Profile.objects.filter(telegram_link_code=code).select_related("user").first()
    if not profile:
        return JsonResponse({"ok": False, "error": "invalid_code"}, status=404)

    profile.telegram_chat_id = chat_id
    profile.telegram_username = username
    profile.telegram_connected_at = timezone.now()
    profile.telegram_link_code = ""
    profile.telegram_link_code_created_at = None
    profile.save(update_fields=[
        "telegram_chat_id",
        "telegram_username",
        "telegram_connected_at",
        "telegram_link_code",
        "telegram_link_code_created_at",
    ])

    return JsonResponse({
        "ok": True,
        "user_id": profile.user_id,
        "username": username,
    })