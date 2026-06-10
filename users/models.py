from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import secrets
import string

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField("ФИО", max_length=255, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    telegram_chat_id = models.CharField("Telegram chat ID", max_length=64, blank=True)
    telegram_username = models.CharField("Telegram username", max_length=255, blank=True)
    telegram_link_code = models.CharField("Код привязки Telegram", max_length=32, blank=True, db_index=True)
    telegram_link_code_created_at = models.DateTimeField("Код создан", null=True, blank=True)
    telegram_connected_at = models.DateTimeField("Telegram подключён", null=True, blank=True)
    telegram_notifications_enabled = models.BooleanField("Включить уведомления в Telegram", default=True)
    telegram_notify_new_lessons = models.BooleanField("Новые уроки", default=True)
    telegram_notify_new_quizzes = models.BooleanField("Новые тесты", default=True)
    telegram_notify_deadlines = models.BooleanField("Приближающиеся дедлайны", default=True)

    @property
    def telegram_is_connected(self) -> bool:
        return bool(self.telegram_chat_id)

    def generate_telegram_link_code(self, length: int = 10) -> str:
        alphabet = string.ascii_uppercase + string.digits
        self.telegram_link_code = "".join(secrets.choice(alphabet) for _ in range(length))
        self.telegram_link_code_created_at = timezone.now()
        return self.telegram_link_code

    def clear_telegram_connection(self):
        self.telegram_chat_id = ""
        self.telegram_username = ""
        self.telegram_connected_at = None
        self.telegram_link_code = ""
        self.telegram_link_code_created_at = None

    def __str__(self):
        return self.full_name or self.user.username


class TelegramBotState(models.Model):
    key = models.CharField(max_length=50, unique=True, default="default")
    last_update_id = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.last_update_id}"


class TelegramNotificationLog(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="telegram_notification_logs")
    unique_key = models.CharField(max_length=255)
    kind = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("profile", "unique_key")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.profile.user.username}: {self.kind or self.unique_key}"