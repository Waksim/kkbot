import logging
from typing import List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from django.conf import settings

from apps.cards.services.db_updater import run_card_update
from apps.users.models import TelegramUser, UserActivity
from apps.users.services import log_user_activity

logger = logging.getLogger(__name__)
admin_router = Router(name="admin-commands-router")

# Применяем фильтр ко всем хендлерам в этом роутере
if settings.ADMIN_ID:
    admin_router.message.filter(F.from_user.id == settings.ADMIN_ID)
else:
    logger.warning("ADMIN_ID не указан в .env, админ-команды будут недоступны.")
    admin_router.message.filter(lambda message: False)  # Блокируем все команды


async def send_long_message(message: Message, text: str, max_length: int = 4096):
    """Отправляет длинное сообщение, разбивая его на части."""
    for i in range(0, len(text), max_length):
        await message.answer(text[i:i + max_length])


@admin_router.message(Command("update_cards"))
async def update_cards_command(message: Message):
    """
    Обрабатывает команду /update_cards, запуская обновление базы карт.
    """
    user = await TelegramUser.objects.aget(user_id=message.from_user.id)
    await log_user_activity(user, UserActivity.ActivityType.COMMAND_USED, {'command': '/update_cards'})

    await message.answer("✅ Команда принята. Начинаю обновление базы данных карт...\n"
                         "Это может занять несколько минут. Я пришлю отчет по завершении.")
    try:
        logs: List[str] = await run_card_update()
        report = "\n".join(logs)
        await send_long_message(message, "📝 **Отчет об обновлении:**\n\n" + report)
        await message.answer("🎉 Обновление завершено!")
    except Exception as e:
        logger.exception("Критическая ошибка при выполнении update_cards_command")
        await message.answer(f"❌ **Произошла критическая ошибка:**\n\n`{e}`")


@admin_router.message(Command("help_admin"))
async def admin_help_command(message: Message):
    """
    Показывает доступные админ-команды.
    """
    user = await TelegramUser.objects.aget(user_id=message.from_user.id)
    await log_user_activity(user, UserActivity.ActivityType.COMMAND_USED, {'command': '/help_admin'})

    await message.answer(
        "**Команды администратора:**\n"
        "/update_cards - Запустить полное обновление базы данных карт из API.\n"
        "/help_admin - Показать это сообщение."
    )