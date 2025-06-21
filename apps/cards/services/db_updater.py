# apps/cards/services/db_updater.py

import asyncio
import httpx
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from django.db import transaction
from django.conf import settings
from apps.cards.models import Card, Tag

# --- Константы ---
GCG_DATA_URL = "https://api.hakush.in/gi/data/gcg.json"
NEW_CARDS_URL = "https://api.hakush.in/gi/new.json"
IMAGE_BASE_URL = "https://api.hakush.in/gi/UI/"
IMAGE_DIR = settings.MEDIA_ROOT / 'card_images'


async def _fetch_json(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Асинхронно получает и декодирует JSON по URL."""
    response = await client.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


async def _download_image(client: httpx.AsyncClient, card: Card, icon_name: str) -> str:
    """Асинхронно скачивает изображение для карты, если его еще нет."""
    local_path: Path = card.local_image_path
    if local_path.exists():
        return f"  - Изображение для {card.name} уже существует."

    image_url = f"{IMAGE_BASE_URL}{icon_name}.webp"
    try:
        async with client.stream("GET", image_url, follow_redirects=True, timeout=30) as response:
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
        return f"  - [СКАЧАНО] Изображение для {card.name} -> {local_path}"
    except httpx.RequestError as e:
        return f"  - [ПРЕДУПРЕЖДЕНИЕ] Не удалось скачать изображение для {card.name} с {e.request.url}"
    except Exception as e:
        return f"  - [ПРЕДУПРЕЖДЕНИЕ] Ошибка при сохранении файла для {card.name}: {e}"


async def _update_tags(card: Card, tag_names: List[str]) -> None:
    """Асинхронно обновляет теги для указанной карты."""
    # Используем `aset` для эффективности в асинхронном контексте
    current_tags = {tag.name async for tag in card.tags.all()}
    tags_to_add_names = set(tag_names) - current_tags
    tags_to_remove_names = current_tags - set(tag_names)

    if tags_to_add_names:
        tags_to_add = [await Tag.objects.aget_or_create(name=tag_name) for tag_name in tags_to_add_names]
        await card.tags.aadd(*[tag for tag, created in tags_to_add])

    if tags_to_remove_names:
        tags_to_remove = Tag.objects.filter(name__in=tags_to_remove_names)
        await card.tags.aremove(*[tag async for tag in tags_to_remove])


# ИСПРАВЛЕНИЕ: Используем transaction.atomic как декоратор.
# Это правильный способ обеспечить атомарность для всей асинхронной функции.
@transaction.atomic
async def run_card_update() -> List[str]:
    """
    Запускает полный процесс обновления базы данных карт и возвращает журнал выполнения.
    Вся функция выполняется в одной транзакции благодаря декоратору @transaction.atomic.
    """
    logs: List[str] = []
    try:
        async with httpx.AsyncClient() as client:
            logs.append("[INFO] Начало процесса обновления базы данных...")
            # 1. Получаем данные
            logs.append(f"  - Загрузка данных с {GCG_DATA_URL}")
            all_cards_data = await _fetch_json(client, GCG_DATA_URL)
            logs.append(f"  - Загрузка данных с {NEW_CARDS_URL}")
            new_cards_data = await _fetch_json(client, NEW_CARDS_URL)
            new_card_ids: Set[int] = set(new_cards_data.get('gcg', []))

            logs.append(f"[INFO] Найдено {len(all_cards_data)} карт в основном файле.")
            logs.append(f"[INFO] Найдено {len(new_card_ids)} 'новых' карт.")

            # 2. Создаем директорию для изображений
            IMAGE_DIR.mkdir(parents=True, exist_ok=True)

            related_cards_to_link: List[Tuple[int, int]] = []
            processed_card_ids: Set[int] = set()

            # --- Проход 1: Создание и обновление карт ---
            # ИСПРАВЛЕНИЕ: Убрали `async with transaction.atomic()`. Вся функция уже атомарна.
            for card_id_str, data in all_cards_data.items():
                card_id = int(card_id_str)
                processed_card_ids.add(card_id)

                card_name = data.get('EN') or f"Unknown Card {card_id}"
                defaults = {
                    'card_type': data.get('type', 'Action'),
                    'name': card_name,
                    'title': data.get('title', ''),
                    'description': data.get('desc', '').replace('\\n', '\n'),
                    'cost_info': data.get('cost', []),
                    'hp': data.get('hp'),
                    'is_new': card_id in new_card_ids,
                }

                card, created = await Card.objects.aupdate_or_create(card_id=card_id, defaults=defaults)

                log_action = "[CREATE]" if created else "[UPDATE]"
                logs.append(f"{log_action} Карта: {card.name} ({card.card_id})")

                # Обновление тегов
                tag_names = data.get('tag', [])
                await _update_tags(card, tag_names)
                if tag_names:
                    logs.append(f"  - Теги для {card.name}: {', '.join(tag_names)}")

                # Скачивание изображения
                if icon_name := data.get('icon'):
                    log_msg = await _download_image(client, card, icon_name)
                    logs.append(log_msg)
                else:
                    logs.append(f"[WARNING] У карты {card.name} ({card.card_id}) нет 'icon', изображение не скачано.")

                # Сохраняем ID для связывания
                if related_id := data.get('relate'):
                    related_cards_to_link.append((card.card_id, int(related_id)))

            # --- Проход 2: Создание связей ---
            logs.append("[INFO] Обновление связей между картами...")
            # ИСПРАВЛЕНИЕ: Убрали `async with transaction.atomic()`.
            for card_id, related_id in related_cards_to_link:
                try:
                    card = await Card.objects.aget(pk=card_id)
                    related_card_obj = await Card.objects.aget(pk=related_id)
                    if card.related_card != related_card_obj:
                        card.related_card = related_card_obj
                        await card.asave(update_fields=['related_card'])
                        logs.append(f"  - Связана карта {card.name} -> {related_card_obj.name}")
                except Card.DoesNotExist:
                    logs.append(f"[WARNING] Не удалось связать {card_id} с {related_id}: карта не найдена.")

            # --- Проход 3: Удаление устаревших карт ---
            stale_cards = Card.objects.exclude(card_id__in=processed_card_ids)
            count = await stale_cards.acount()
            if count > 0:
                logs.append(f"[DELETE] Найдено и удалено {count} устаревших карт.")
                await stale_cards.adelete()

    except httpx.HTTPStatusError as e:
        logs.append(f"[ERROR] HTTP Ошибка: {e.response.status_code} при запросе к {e.request.url}")
        # В случае ошибки транзакция откатится автоматически благодаря декоратору
    except Exception as e:
        logs.append(f"[CRITICAL] Непредвиденная ошибка: {e}")
        # Транзакция также будет отменена
        raise # Поднимаем исключение дальше, чтобы увидеть traceback
    else:
        logs.append("[SUCCESS] База данных успешно обновлена!")

    return logs