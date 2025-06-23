# apps/cards/services/db_updater.py

import asyncio
import httpx
import logging
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from asgiref.sync import async_to_sync
from django.db import transaction
from django.conf import settings
from apps.cards.models import Card, Tag

logger = logging.getLogger(__name__)

# --- Константы ---
# Источники данных для карт.
GCG_DATA_URL = "https://api.hakush.in/gi/data/gcg.json"  # Полная база карт
NEW_CARDS_URL = "https://api.hakush.in/gi/new.json"      # Список ID новых карт
# Базовый URL для загрузки изображений карт.
IMAGE_BASE_URL = "https://api.hakush.in/gi/UI/"
# Локальная директория для сохранения изображений.
IMAGE_DIR = settings.MEDIA_ROOT / 'card_images'


# --- Асинхронные хелперы ---

async def _fetch_all_data_async() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Асинхронно получает все данные о картах и список новых карт."""
    async with httpx.AsyncClient() as client:
        # Запускаем загрузку двух JSON-файлов параллельно для ускорения.
        all_cards_task = asyncio.create_task(_fetch_json(client, GCG_DATA_URL))
        new_cards_task = asyncio.create_task(_fetch_json(client, NEW_CARDS_URL))
        # Ожидаем завершения обеих задач.
        all_cards_data, new_cards_data = await asyncio.gather(all_cards_task, new_cards_task)
    return all_cards_data, new_cards_data


async def _fetch_json(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Асинхронно загружает и декодирует JSON по указанному URL."""
    try:
        response = await client.get(url, timeout=30)
        response.raise_for_status()  # Вызовет исключение для кодов ответа 4xx/5xx.
        return response.json()
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
        logger.error(f"Не удалось получить или декодировать JSON с {url}: {e}")
        return {}


async def _download_images_async(images_to_download: Dict[Path, str]):
    """Асинхронно и параллельно скачивает изображения."""

    async def _download_one(client: httpx.AsyncClient, local_path: Path, url: str):
        try:
            # Используем `client.stream` для потоковой загрузки больших файлов (изображений).
            async with client.stream("GET", url, follow_redirects=True, timeout=20) as r:
                r.raise_for_status()
                # ВАЖНО: `open` является блокирующей (синхронной) операцией. В идеале здесь
                # следует использовать `aiofiles` или `asyncio.to_thread`, чтобы не
                # блокировать event loop.
                with open(local_path, 'wb') as f:
                    async for chunk in r.aiter_bytes():
                        f.write(chunk)
        except Exception:
            # Логируем только URL, чтобы не загромождать логи полным traceback-ом
            # при массовых сбоях (например, недоступности сервера изображений).
            logger.warning(f"Не удалось скачать изображение: {url}", exc_info=False)

    async with httpx.AsyncClient() as client:
        # Создаем список задач для параллельного выполнения.
        tasks = [_download_one(client, path, url) for path, url in images_to_download.items()]
        await asyncio.gather(*tasks)


async def _get_images_to_download_async(
        processed_card_ids: Set[int], all_cards_data: Dict[str, Any]
) -> Dict[Path, str]:
    """
    Асинхронно формирует словарь изображений для скачивания,
    проверяя наличие файлов на диске.
    """
    image_map = {}
    cards_qs = Card.objects.filter(card_id__in=processed_card_ids)

    # Итерируемся по картам, которые должны быть в нашей БД.
    async for card in cards_qs:
        # ВАЖНО: `card.local_image_path.exists()` является блокирующей (синхронной)
        # операцией, которая обращается к файловой системе. Это может замедлить
        # event loop при большом количестве карт.
        if not card.local_image_path.exists():
            # Если изображения нет, и в данных API есть иконка, добавляем в очередь на скачивание.
            if icon := all_cards_data.get(str(card.card_id), {}).get('icon'):
                image_map[card.local_image_path] = f"{IMAGE_BASE_URL}{icon}.webp"
    return image_map


async def _db_operations_async(all_cards_data: Dict[str, Any], new_card_ids: Set[int]) -> Set[int]:
    """
    Выполняет все операции с базой данных в одной асинхронной функции.
    Включает создание, обновление и удаление карт, а также управление тегами.
    Предполагается, что эта функция будет вызвана внутри транзакции.
    """
    processed_card_ids: Set[int] = set()

    # --- Проход 1: Создание/обновление карт БЕЗ внешних ключей ---
    # Загружаем все существующие карты в словарь для быстрого доступа в памяти.
    existing_cards = {c.card_id: c async for c in Card.objects.all()}
    cards_to_update, cards_to_create = [], []
    related_card_map: Dict[int, int] = {}  # Для отложенной установки связей 'related_card'

    # Готовим объекты Card для массового создания и обновления.
    for card_id_str, data in all_cards_data.items():
        if not (isinstance(data, dict) and data.get('EN')): continue

        card_id = int(card_id_str)
        processed_card_ids.add(card_id)

        if related_id := data.get('relate'):
            related_card_map[card_id] = int(related_id)

        # Словарь с данными для создания/обновления.
        defaults = {
            'card_type': data.get('type', 'Action'), 'name': data['EN'],
            'title': data.get('title', ''), 'description': data.get('desc', '').replace('\\n', '\n'),
            'cost_info': data.get('cost', []), 'hp': data.get('hp'),
            'is_new': card_id in new_card_ids,
            'related_card_id': None  # Внешние ключи устанавливаются на втором проходе.
        }

        if card_id in existing_cards:
            card_obj = existing_cards[card_id]
            for key, value in defaults.items(): setattr(card_obj, key, value)
            cards_to_update.append(card_obj)
        else:
            cards_to_create.append(Card(card_id=card_id, **defaults))

    # Выполняем массовые операции для производительности.
    update_fields = list(defaults.keys())
    if cards_to_update:
        await Card.objects.abulk_update(cards_to_update, fields=update_fields)
    if cards_to_create:
        await Card.objects.abulk_create(cards_to_create)

    # --- Проход 2: Установка внешних ключей (связей) ---
    cards_to_update_relations = []
    # Снова получаем все карты (включая только что созданные).
    all_processed_cards_map = {c.card_id: c async for c in Card.objects.filter(card_id__in=processed_card_ids)}

    for card_id, related_id in related_card_map.items():
        if card_id in all_processed_cards_map and related_id in all_processed_cards_map:
            card = all_processed_cards_map[card_id]
            card.related_card_id = related_id
            cards_to_update_relations.append(card)

    if cards_to_update_relations:
        await Card.objects.abulk_update(cards_to_update_relations, fields=['related_card_id'])

    # --- Проход 3: Обновление тегов (после создания всех карт) ---
    all_processed_cards = {c.card_id: c async for c in
                           Card.objects.filter(card_id__in=processed_card_ids).prefetch_related('tags')}

    # Собираем все уникальные имена тегов из API.
    tag_names_to_create = {tag for data in all_cards_data.values() for tag in data.get('tag', [])}
    # Создаем недостающие теги в БД одним запросом.
    await Tag.objects.abulk_create([Tag(name=n) for n in tag_names_to_create], ignore_conflicts=True)
    # Загружаем все теги из БД в словарь для быстрого доступа.
    all_db_tags = {t.name: t async for t in Tag.objects.all()}

    # Устанавливаем связи между картами и тегами.
    # ВНИМАНИЕ: Этот цикл может приводить к проблеме "N+1 запросов", так как `card.tags.aset`
    # для каждой карты выполняет отдельные операции с БД (DELETE, INSERT).
    for card in all_processed_cards.values():
        api_data = all_cards_data.get(str(card.card_id), {})
        tag_names = api_data.get('tag', [])
        # `aset` очищает старые теги и устанавливает новые.
        await card.tags.aset([all_db_tags[name] for name in tag_names if name in all_db_tags])

    # --- Проход 4: Удаление устаревших карт ---
    # Удаляем карты, которые есть в БД, но отсутствуют в последней версии API.
    await Card.objects.exclude(card_id__in=processed_card_ids).adelete()

    return processed_card_ids


# --- Основная синхронная функция-оркестратор ---

def run_card_update() -> List[str]:
    """
    Синхронная функция-оркестратор. Запускает асинхронные блоки для сети
    и выполняет операции с БД в транзакции, используя мосты async/sync.
    Возвращает список логов для отображения пользователю.
    """
    logs: List[str] = ["[INFO] Начало процесса обновления..."]

    # Этап 1: Загрузка данных из API
    try:
        logs.append("[INFO] Этап 1: Загрузка данных из API.")
        all_cards_data, new_cards_data = asyncio.run(_fetch_all_data_async())
        if not all_cards_data:
            raise RuntimeError("Не удалось получить основной список карт.")
    except Exception as e:
        logs.append(f"[CRITICAL] Ошибка при загрузке данных API: {e}")
        return logs

    # Этап 2: Обновление БД в атомарной транзакции
    try:
        logs.append("[INFO] Этап 2: Обновление базы данных в транзакции.")
        # `transaction.atomic` гарантирует, что все операции с БД либо пройдут успешно, либо будут отменены.
        with transaction.atomic():
            # `async_to_sync` позволяет вызвать асинхронную функцию из синхронного контекста.
            processed_card_ids = async_to_sync(_db_operations_async)(
                all_cards_data, set(new_cards_data.get('gcg', []))
            )
        logs.append("[SUCCESS] Транзакция с базой данных успешно завершена.")
    except Exception as e:
        logger.critical("Критическая ошибка в транзакции БД", exc_info=True)
        logs.append(f"[CRITICAL] Ошибка транзакции: {e}. Изменения отменены.")
        return logs

    # Этап 3: Скачивание недостающих изображений
    try:
        logs.append("[INFO] Этап 3: Поиск и скачивание недостающих изображений.")
        # `async_to_sync` для вызова асинхронной функции.
        images_to_download = async_to_sync(_get_images_to_download_async)(
            processed_card_ids, all_cards_data
        )
        if images_to_download:
            IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            logs.append(f"Обнаружено {len(images_to_download)} изображений для скачивания.")
            asyncio.run(_download_images_async(images_to_download))
            logs.append("[DOWNLOAD] Скачивание завершено.")
        else:
            logs.append("Все изображения уже на месте.")
    except Exception as e:
        logs.append(f"[WARNING] Ошибка во время скачивания изображений: {e}")

    logs.append("[SUCCESS] Процесс обновления полностью завершен!")
    return logs