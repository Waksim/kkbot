import asyncio
import logging
from django.core.management.base import BaseCommand
import django


class Command(BaseCommand):
    help = "Запускает телеграм-бота"

    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )

        self.stdout.write(self.style.SUCCESS("Запуск телеграм-бота..."))

        # `django.setup()` необходим для инициализации Django и доступа к моделям перед запуском бота.
        django.setup()

        # Импортируем `main` здесь, чтобы Django успел полностью настроиться.
        from apps.bot.main import main

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Бот остановлен вручную."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Произошла критическая ошибка: {e}"))