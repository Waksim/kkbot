import asyncio
import logging
from django.conf import settings
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apps.bot.handlers import deck_codes, admin_commands


async def main() -> None:
    """
    Инициализирует и запускает бота.
    """
    if not settings.BOT_TOKEN:
        logging.error("Необходимо указать BOT_TOKEN в .env файле.")
        return
    if not settings.ADMIN_ID:
        logging.warning("ADMIN_ID не указан в .env. Админ-команды не будут работать.")

    # Инициализируем бота с `DefaultBotProperties`, чтобы задать `parse_mode` по умолчанию для всех запросов.
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    dp.include_router(admin_commands.admin_router)
    dp.include_router(deck_codes.router)

    await dp.start_polling(bot)