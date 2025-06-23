import asyncio
import csv
import logging
from pathlib import Path
from typing import Any, List, Set
from datetime import datetime, timezone as dt_timezone

from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.users.models import Deck

logger = logging.getLogger(__name__)


@sync_to_async
@transaction.atomic
def _save_decks_in_transaction(decks_to_save: List[Deck]) -> None:
    """
    Синхронная обертка для атомарного массового создания объектов Deck.
    Декоратор @sync_to_async позволяет вызывать эту функцию из асинхронного кода.
    Декоратор @transaction.atomic обеспечивает, что все операции внутри
    будут выполнены в одной транзакции.
    """
    Deck.objects.bulk_create(decks_to_save, batch_size=500)


class Command(BaseCommand):
    """
    Импортирует предустановленные колоды из CSV-файла в базу данных.
    """
    help = "Импортирует колоды из CSV-файла в базу данных."

    def add_arguments(self, parser: CommandParser) -> None:
        """Добавляет аргументы командной строки."""
        parser.add_argument(
            '--path',
            type=str,
            default='data/decks.csv',
            help='Путь к CSV-файлу с колодами относительно корня проекта.'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Синхронная точка входа, которая запускает асинхронную логику."""
        try:
            asyncio.run(self.ahandle(*args, **options))
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(
                f"Файл не найден по пути: {options['path']}. "
                "Убедитесь, что файл существует и путь указан верно."
            ))
        except Exception as e:
            logger.exception("Критическая ошибка во время импорта колод.")
            self.stderr.write(self.style.ERROR(f"Произошла непредвиденная ошибка: {e}"))

    async def ahandle(self, *args: Any, **options: Any) -> None:
        """Основная асинхронная логика команды."""
        file_path: Path = settings.BASE_DIR / options['path']
        self.stdout.write(self.style.SUCCESS(f"Начинаю импорт колод из файла: {file_path}"))

        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                required_fields = ['deck_code', 'character_cards', 'action_cards', 'created_at']
                if not all(field in reader.fieldnames for field in required_fields):
                    self.stderr.write(self.style.ERROR(
                        f"CSV-файл должен содержать обязательные колонки: {', '.join(required_fields)}"))
                    return
                csv_data = list(reader)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка чтения CSV файла: {e}"))
            return

        if not csv_data:
            self.stdout.write(self.style.WARNING("CSV-файл пуст."))
            return

        csv_deck_codes = {row['deck_code'] for row in csv_data}
        existing_codes_qs = Deck.objects.filter(deck_code__in=csv_deck_codes).values_list('deck_code', flat=True)
        existing_codes: Set[str] = {code async for code in existing_codes_qs}
        self.stdout.write(f"Найдено {len(existing_codes)} уже существующих колод в БД. Они будут пропущены.")

        decks_to_create: List[Deck] = []
        for row in csv_data:
            deck_code = row['deck_code']
            if not deck_code or deck_code in existing_codes:
                continue

            try:
                character_ids = [int(id_str) for id_str in row['character_cards'].split(',') if id_str.isdigit()]
                action_ids = [int(id_str) for id_str in row['action_cards'].split(',') if id_str.isdigit()]
                created_at_naive = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
                created_at_dt = timezone.make_aware(created_at_naive, dt_timezone.utc)
                decks_to_create.append(
                    Deck(
                        deck_code=deck_code,
                        character_card_ids=character_ids,
                        action_card_ids=action_ids,
                        created_at=created_at_dt,
                        owner=None
                    )
                )
            except (ValueError, TypeError) as e:
                self.stderr.write(self.style.WARNING(f"Пропуск строки для кода {deck_code} из-за ошибки данных: {e}"))

        if not decks_to_create:
            self.stdout.write(
                self.style.SUCCESS("\nВсе колоды из файла уже есть в базе данных. Обновление не требуется."))
            return

        try:
            await _save_decks_in_transaction(decks_to_create)
            self.stdout.write(self.style.SUCCESS(f"\nУспешно импортировано {len(decks_to_create)} новых колод."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\nОшибка при массовом добавлении в БД: {e}"))
            # В случае ошибки выводим промежуточную статистику для отладки.
            self.stdout.write("-" * 30)
            self.stdout.write(f"Всего обработано строк в файле: {len(csv_data)}")
            self.stdout.write(f"Пропущено (уже в БД): {len(existing_codes)}")
            self.stdout.write(f"Подготовлено к добавлению: {len(decks_to_create)}")
            return

        # Выводим итоговую статистику по результатам импорта.
        self.stdout.write("-" * 30)
        self.stdout.write(f"Всего обработано строк в файле: {len(csv_data)}")
        self.stdout.write(f"Пропущено (уже в БД): {len(existing_codes)}")
        self.stdout.write(f"Добавлено новых колод: {len(decks_to_create)}")
        self.stdout.write(self.style.SUCCESS("Импорт завершен."))