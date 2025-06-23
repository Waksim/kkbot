import logging
from typing import Any
from django.core.management.base import BaseCommand
from apps.cards.services.db_updater import run_card_update


class Command(BaseCommand):
    help = "Заполняет или обновляет базу данных карт из удаленных JSON-файлов."

    def handle(self, *args: Any, **options: Any) -> None:
        """Синхронная точка входа, запускающая сервис обновления."""
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        self.stdout.write("Запуск обновления базы данных...")

        try:
            logs = run_card_update()

            for log_line in logs:
                if "[CRITICAL]" in log_line or "[ERROR]" in log_line:
                    self.stderr.write(self.style.ERROR(log_line))
                elif "[WARNING]" in log_line:
                    self.stdout.write(self.style.WARNING(log_line))
                elif "[SUCCESS]" in log_line:
                    self.stdout.write(self.style.SUCCESS(log_line))
                else:
                    self.stdout.write(log_line)

        except Exception as e:
            # Логгер из сервиса уже должен был записать traceback.
            self.stderr.write(self.style.ERROR(f"Произошла непредвиденная ошибка верхнего уровня: {e}"))