import logging

from aiogram import Router, F
from django.conf import settings

logger = logging.getLogger(__name__)
admin_router = Router(name="admin-commands-router")

# Фильтр, который будет применен ко всем хендлерам в этом роутере.
# Он разрешает доступ к командам только пользователю, чей ID указан в settings.ADMIN_ID.
if settings.ADMIN_ID:
    admin_router.message.filter(F.from_user.id == settings.ADMIN_ID)
else:
    logger.warning("ADMIN_ID не указан в .env, админ-команды будут недоступны.")
    # Если ADMIN_ID не найден, этот фильтр будет всегда возвращать False, блокируя доступ.
    admin_router.message.filter(lambda message: False)