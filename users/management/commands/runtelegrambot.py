from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from users.models import TelegramBotState
from users.telegram import PollLoopState, fetch_updates, process_telegram_update, telegram_is_configured


class Command(BaseCommand):
    help = "Запускает Telegram-бота платформы через long polling."

    def handle(self, *args, **options):
        if not telegram_is_configured():
            raise CommandError("Не задан TELEGRAM_BOT_TOKEN в .env")

        state, _ = TelegramBotState.objects.get_or_create(key="default")
        loop_state = PollLoopState()
        poll_timeout = int(getattr(settings, "TELEGRAM_BOT_POLL_TIMEOUT", 30) or 30)

        self.stdout.write(self.style.SUCCESS("Telegram-бот запущен."))

        try:
            while True:
                try:
                    updates = fetch_updates(offset=state.last_update_id + 1, timeout=poll_timeout)
                except Exception as exc:
                    self.stderr.write(f"Ошибка получения обновлений Telegram: {exc}")
                    loop_state.backoff(3)
                    continue

                for update in updates:
                    update_id = int(update.get("update_id", 0))
                    if update_id > state.last_update_id:
                        process_telegram_update(update)
                        state.last_update_id = update_id
                        state.save(update_fields=["last_update_id", "updated_at"])

                loop_state.maybe_send_deadlines()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Telegram-бот остановлен."))
