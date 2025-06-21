import asyncio
import logging
from django.core.management.base import BaseCommand
import django


class Command(BaseCommand):
    help = "Запускает телеграм-бота"

    def handle(self, *args, **options):
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )

        self.stdout.write(self.style.SUCCESS("Запуск телеграм-бота..."))

        # Настройка Django для асинхронного контекста
        django.setup()

        from apps.bot.main import main  # Импортируем здесь, чтобы Django успел настроиться

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Бот остановлен вручную."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Произошла критическая ошибка: {e}"))