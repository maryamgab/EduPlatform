from django.core.management.base import BaseCommand

from users.telegram import send_upcoming_deadline_notifications


class Command(BaseCommand):
    help = "Отправляет Telegram-напоминания о ближайших дедлайнах."

    def handle(self, *args, **options):
        sent = send_upcoming_deadline_notifications()
        self.stdout.write(self.style.SUCCESS(f"Отправлено напоминаний: {sent}"))
