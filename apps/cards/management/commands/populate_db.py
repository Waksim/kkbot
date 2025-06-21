import asyncio
from typing import Any
from django.core.management.base import BaseCommand
from apps.cards.services.db_updater import run_card_update


class Command(BaseCommand):
    help = "Заполняет или обновляет базу данных карт из удаленных JSON-файлов."

    def handle(self, *args: Any, **options: Any) -> None:
        """Синхронная точка входа, запускающая асинхронный сервис."""
        self.stdout.write("Запуск асинхронного обновления базы данных...")
        try:
            logs = asyncio.run(run_card_update())
            for log_line in logs:
                if "[ERROR]" in log_line or "[CRITICAL]" in log_line:
                    self.stderr.write(self.style.ERROR(log_line))
                elif "[WARNING]" in log_line:
                    self.stdout.write(self.style.WARNING(log_line))
                elif "[SUCCESS]" in log_line:
                    self.stdout.write(self.style.SUCCESS(log_line))
                else:
                    self.stdout.write(log_line)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Произошла критическая ошибка во время выполнения: {e}"))