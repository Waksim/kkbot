from typing import Dict, Any

from apps.users.models import TelegramUser, UserActivity


async def log_user_activity(
    user: TelegramUser,
    activity_type: UserActivity.ActivityType,
    details: Dict[str, Any]
) -> None:
    """
    Асинхронно создает запись о действии пользователя в базе данных.

    Args:
        user: Экземпляр модели TelegramUser.
        activity_type: Тип действия из UserActivity.ActivityType.
        details: Словарь с дополнительной информацией (текст сообщения, код колоды и т.д.).
    """
    await UserActivity.objects.acreate(
        user=user,
        activity_type=activity_type,
        details=details
    )