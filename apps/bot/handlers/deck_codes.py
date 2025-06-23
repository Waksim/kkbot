import re
import logging
import asyncio
from typing import List, Tuple, Optional

from aiogram import Router, F
from aiogram.enums import ChatType, ParseMode
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, InputMediaPhoto
from aiogram.utils.markdown import hbold, hcode

from apps.users.models import TelegramUser, Deck, UserActivity
from apps.cards.models import Card
from apps.bot.services.hoyolab import decode_deck_code
from apps.bot.services.deck_utils import calculate_resonances
from apps.bot.services.image_generator import create_deck_image
from apps.users.services import log_user_activity

router = Router(name="deck-codes-router")
DECK_CODE_REGEX = re.compile(r'([^.,\'\"\s\n\t\r]{68})')
MAX_CODES_PER_MESSAGE = 20  # Ограничение на количество кодов в одном сообщении для предотвращения спама

HELP_TEXT_PRIVATE = (
    f"👋 Привет! Я бот для работы с колодами <b>Genshin Impact TCG</b>.\n\n"
    f"Просто отправь мне код колоды (например, <code>EiFyxd4NFkHyyuENH5ECzGMNF7Eh0p0OChLB6J4PCgHS9TUQFFFC958RGrLhEsMXDZEB</code>), и я:\n"
    f"1. Расшифрую ее состав.\n"
    f"2. Рассчитаю элементальные резонансы.\n"
    f"3. Сгенерирую и пришлю красивое изображение со всеми картами.\n\n"
    f"Ты можешь отправить до {MAX_CODES_PER_MESSAGE} кодов в одном сообщении, и я обработаю их все!"
)


async def get_cards_from_ids_with_duplicates(card_ids: List[int]) -> List[Card]:
    """
    Эффективно получает список объектов Card из списка ID, сохраняя дубликаты
    и предзагружая связанные теги для оптимизации.
    """
    if not card_ids:
        return []

    unique_card_ids = set(card_ids)
    cards_qs = Card.objects.filter(
        card_id__in=unique_card_ids
    ).prefetch_related('tags')
    cards_map = {card.card_id: card async for card in cards_qs}

    result_cards = [cards_map[card_id] for card_id in card_ids if card_id in cards_map]

    return result_cards


async def get_or_create_deck(code: str, user: TelegramUser) -> Tuple[Optional[Deck], Optional[str]]:
    """
    Проверяет наличие колоды в БД (кэш). Если нет - обращается к API,
    проверяет наличие всех карт в нашей БД и создает новую запись Deck.
    Возвращает (Deck, None) при успехе или (None, "сообщение об ошибке") при неудаче.
    """
    try:
        deck = await Deck.objects.aget(deck_code=code)
        return deck, None
    except Deck.DoesNotExist:
        pass

    decoded_deck, error_message = await decode_deck_code(code)
    if error_message:
        return None, error_message
    if not decoded_deck:
        return None, "API не вернуло данные о колоде."

    all_api_ids = set(decoded_deck.character_ids) | set(decoded_deck.action_ids)
    cards_in_db_count = await Card.objects.filter(card_id__in=all_api_ids).acount()

    if cards_in_db_count != len(all_api_ids):
        found_ids = {c.card_id async for c in Card.objects.filter(card_id__in=all_api_ids)}
        missing_ids = all_api_ids - found_ids
        logging.warning(f"Не найдены карты с ID: {missing_ids}")
        return None, f"Некоторые карты отсутствуют в базе. ID: {missing_ids}"

    deck = await Deck.objects.acreate(
        deck_code=code,
        owner=user,
        character_card_ids=decoded_deck.character_ids,
        action_card_ids=decoded_deck.action_ids
    )
    return deck, None


async def process_message_with_codes(message: Message, text_to_parse: str):
    """
    Основная логика обработки сообщения с кодами, генерации изображений и отправки альбома.
    """
    user_data = message.from_user
    user, _ = await TelegramUser.objects.aupdate_or_create(
        user_id=user_data.id,
        defaults={
            'username': user_data.username,
            'first_name': user_data.first_name,
            'last_name': user_data.last_name,
        }
    )

    await log_user_activity(
        user,
        UserActivity.ActivityType.MESSAGE_RECEIVED,
        {'text': message.text or "Сообщение без текста"}
    )

    deck_codes = DECK_CODE_REGEX.findall(text_to_parse)
    if not deck_codes:
        await log_user_activity(user, UserActivity.ActivityType.EMPTY_REQUEST, {'text': text_to_parse})
        if message.chat.type == ChatType.PRIVATE:
            await message.reply(HELP_TEXT_PRIVATE)
        else:
            await message.reply("Не найдены коды колод в вашем сообщении.")
        return

    if len(deck_codes) > MAX_CODES_PER_MESSAGE:
        await message.reply(
            f"Найдено слишком много кодов ({len(deck_codes)}). "
            f"Будут обработаны только первые {MAX_CODES_PER_MESSAGE}."
        )
        deck_codes = deck_codes[:MAX_CODES_PER_MESSAGE]

    media_items: List[InputMediaPhoto] = []
    caption_lines: List[str] = []
    error_messages: List[str] = []

    processing_message = await message.reply(f"Начинаю обработку {len(deck_codes)} колод...")

    for index, code in enumerate(deck_codes):
        deck_obj, error_message = await get_or_create_deck(code, user)

        if error_message:
            error_text = f"❌ Ошибка с кодом {hcode(code)}:\n   {error_message}"
            error_messages.append(error_text)
            await log_user_activity(
                user,
                UserActivity.ActivityType.INVALID_CODE,
                {'code': code, 'error': error_message}
            )
            continue
        if not deck_obj:
            error_text = f"❌ Неизвестная ошибка с кодом {hcode(code)}"
            error_messages.append(error_text)
            await log_user_activity(
                user,
                UserActivity.ActivityType.ERROR_OCCURRED,
                {'code': code, 'context': 'get_or_create_deck_returned_none'}
            )
            continue

        await log_user_activity(user, UserActivity.ActivityType.DECK_PROCESSED, {'code': code})

        character_cards = await get_cards_from_ids_with_duplicates(deck_obj.character_card_ids)
        action_cards = await get_cards_from_ids_with_duplicates(deck_obj.action_card_ids)

        resonances = calculate_resonances(character_cards)

        image_bytes = await asyncio.to_thread(
            create_deck_image, character_cards, action_cards, resonances
        )
        photo_file = BufferedInputFile(image_bytes.read(), filename=f"{code}.jpg")

        media_items.append(InputMediaPhoto(media=photo_file))

        unique_char_names = sorted(list(set(card.name for card in character_cards)))
        caption_chars = ", ".join([hbold(name) for name in unique_char_names])
        caption_lines.append(f"{index + 1}) {caption_chars} {hcode(code)}")

    await processing_message.delete()

    # --- Отправка результатов ---
    if media_items:
        final_caption = "\n\n".join(caption_lines)

        if len(media_items) == 1:
            await message.reply_photo(photo=media_items[0].media, caption=final_caption)
        else:
            media_items[0].caption = final_caption
            media_items[0].parse_mode = ParseMode.HTML

            for i in range(0, len(media_items), 10):
                chunk = media_items[i:i + 10]
                await message.reply_media_group(media=chunk)

    if error_messages:
        await message.reply("Возникли следующие ошибки:\n\n" + "\n".join(error_messages))


@router.message(Command("kk", "кк", ignore_case=True), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_deck_codes_group(message: Message, command: Command):
    """
    Обрабатывает команду /kk в группах.
    """
    text_to_parse = command.args
    if not text_to_parse:
        await message.reply("Пожалуйста, укажите коды колод после команды /kk.")
        return
    await process_message_with_codes(message, text_to_parse)


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def handle_deck_codes_private(message: Message):
    """
    Обрабатывает сообщения с кодами в личных чатах.
    """
    if not message.text:
        return
    await process_message_with_codes(message, message.text)