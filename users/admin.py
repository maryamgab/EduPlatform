from django.contrib import admin

from .models import Profile, TelegramBotState, TelegramNotificationLog


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "telegram_chat_id",
        "telegram_username",
        "telegram_connected_at",
    )
    search_fields = ("user__username", "user__email", "full_name", "telegram_username", "telegram_chat_id")
    readonly_fields = ("telegram_connected_at", "telegram_link_code_created_at")


@admin.register(TelegramBotState)
class TelegramBotStateAdmin(admin.ModelAdmin):
    list_display = ("key", "last_update_id", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(TelegramNotificationLog)
class TelegramNotificationLogAdmin(admin.ModelAdmin):
    list_display = ("profile", "kind", "unique_key", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("profile__user__username", "profile__user__email", "unique_key")
    readonly_fields = ("created_at",)
