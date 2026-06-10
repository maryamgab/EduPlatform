from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="telegram_chat_id",
            field=models.CharField(blank=True, max_length=64, verbose_name="Telegram chat ID"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_connected_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Telegram подключён"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_link_code",
            field=models.CharField(blank=True, db_index=True, max_length=32, verbose_name="Код привязки Telegram"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_link_code_created_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Код создан"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_notifications_enabled",
            field=models.BooleanField(default=True, verbose_name="Включить уведомления в Telegram"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_notify_deadlines",
            field=models.BooleanField(default=True, verbose_name="Приближающиеся дедлайны"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_notify_new_lessons",
            field=models.BooleanField(default=True, verbose_name="Новые уроки"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_notify_new_quizzes",
            field=models.BooleanField(default=True, verbose_name="Новые тесты"),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_username",
            field=models.CharField(blank=True, max_length=255, verbose_name="Telegram username"),
        ),
    ]
