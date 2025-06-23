import asyncio
import logging
from pathlib import Path
from typing import Optional, List

from django.core.management.base import BaseCommand
from django.conf import settings

from apps.bot.handlers.deck_codes import get_or_create_deck, get_cards_from_ids_with_duplicates
from apps.bot.services.deck_utils import calculate_resonances
from apps.bot.services.image_generator import create_deck_image
from apps.bot.tests.test_data import DECK_TEST_CASES
from apps.users.models import TelegramUser

# Устанавливаем уровень логирования, чтобы видеть предупреждения от генератора изображений
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Создает и сохраняет изображение колоды по ее коду для быстрой визуальной проверки.

    Эта команда не отображает изображение на экране, а сохраняет его в файл
    `media/test_deck_image.jpg`, что надежно работает в любой среде, включая Docker.

    Примеры использования:
    1. Убедитесь, что база данных карт заполнена:
       docker-compose exec web python manage.py populate_db

    2. Запуск с тестовой колодой по умолчанию:
       docker-compose exec web python manage.py generate_test_image

    3. Запуск с конкретным кодом колоды:
       docker-compose exec web python manage.py generate_test_image ADDQyv4PBLEQCM4QCxDQC9kQCxGxDLUMDCEBCN4QDNECDPYQDEAA
    """
    help = "Генерирует тестовое изображение для кода колоды и сохраняет его в 'media/test_deck_image.jpg'."

    def add_arguments(self, parser):
        parser.add_argument(
            'deck_code',
            nargs='?',  # Аргумент необязательный
            type=str,
            default=None,
            help='Код колоды. Если не указан, используется первая колода из тестового набора.'
        )

    def handle(self, *args, **options):
        """
        Синхронная точка входа, которая запускает асинхронную логику.
        """
        try:
            asyncio.run(self.ahandle(*args, **options))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Выполнение прервано пользователем."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Произошла критическая ошибка: {e}"))


    async def ahandle(self, *args, **options):
        """
        Основная асинхронная логика команды.
        """
        deck_code_arg: Optional[str] = options['deck_code']
        character_ids: List[int] = []
        action_ids: List[int] = []

        if deck_code_arg:
            self.stdout.write(self.style.SUCCESS(f"Обработка указанного кода колоды: {deck_code_arg}"))
            # Для вызова `get_or_create_deck` требуется объект TelegramUser. Создадим или получим тестового.
            user, _ = await TelegramUser.objects.aget_or_create(
                user_id=0,
                defaults={'first_name': 'Test Image Generator'}
            )

            deck_obj, error_message = await get_or_create_deck(deck_code_arg, user)

            if error_message:
                self.stderr.write(self.style.ERROR(f"Ошибка получения колоды: {error_message}"))
                return
            if not deck_obj:
                self.stderr.write(self.style.ERROR("Не удалось получить объект колоды."))
                return

            character_ids = deck_obj.character_card_ids
            action_ids = deck_obj.action_card_ids
        else:
            # Используем данные из `test_data`, чтобы команда не зависела от доступности внешнего API.
            test_case = DECK_TEST_CASES[0]
            deck_code_arg = test_case.deck_code
            self.stdout.write(
                self.style.WARNING(f"Код не указан. Используется тестовый код: {deck_code_arg}")
            )
            character_ids = test_case.character_ids
            action_ids = test_case.action_ids

        # --- Общая логика для обоих случаев ---

        self.stdout.write("  - Загрузка объектов карт из локальной БД...")
        character_cards = await get_cards_from_ids_with_duplicates(character_ids)
        action_cards = await get_cards_from_ids_with_duplicates(action_ids)

        if not character_cards or len(action_cards) != len(action_ids):
            self.stderr.write(self.style.ERROR(
                "Некоторые карты не найдены в локальной базе данных.\n"
                "Убедитесь, что вы запустили команду `populate_db` и "
                "что она отработала без ошибок для всех необходимых карт."
            ))
            return

        self.stdout.write("  - Вычисление элементальных резонансов...")
        # Резонансы вычисляются синхронно, так как все необходимые данные (карты и теги) уже загружены в память.
        resonances = calculate_resonances(character_cards)
        self.stdout.write(f"  - Обнаружены резонансы: {resonances or 'Нет'}")

        self.stdout.write("  - Генерация изображения...")
        # `create_deck_image` — это ресурсоемкая операция (работа с Pillow),
        # поэтому выносим ее в отдельный поток, чтобы не блокировать event loop.
        image_bytes = await asyncio.to_thread(
            create_deck_image, character_cards, action_cards, resonances
        )

        output_dir: Path = settings.MEDIA_ROOT
        output_dir.mkdir(parents=True, exist_ok=True)  # Создаем папку /media, если ее нет
        output_path = output_dir / 'test_deck_image.jpg'

        try:
            with open(output_path, 'wb') as f:
                f.write(image_bytes.getbuffer())
            self.stdout.write(self.style.SUCCESS(
                f"\nИзображение успешно сгенерировано и сохранено!\n"
                f"Путь к файлу: {output_path.relative_to(settings.BASE_DIR)}"
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Не удалось сохранить изображение: {e}"))