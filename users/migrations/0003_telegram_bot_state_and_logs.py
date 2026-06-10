from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_profile_telegram_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramBotState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(default="default", max_length=50, unique=True)),
                ("last_update_id", models.BigIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="TelegramNotificationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("unique_key", models.CharField(max_length=255)),
                ("kind", models.CharField(blank=True, max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "profile",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="telegram_notification_logs", to="users.profile"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("profile", "unique_key")},
            },
        ),
    ]
