from django.db import models
from django.contrib import admin
from django.utils.html import format_html


class TelegramUser(models.Model):
    """Модель для хранения информации о пользователях Telegram."""
    user_id = models.BigIntegerField(
        primary_key=True,
        verbose_name="Telegram User ID"
    )
    username = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Username"
    )
    first_name = models.CharField(
        max_length=255,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Фамилия"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата регистрации"
    )

    class Meta:
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"
        ordering = ['-created_at']

    @admin.display(description='Количество колод')
    def deck_count(self) -> int:
        """Возвращает количество колод, отправленных пользователем."""
        return self.decks.count()

    def __str__(self) -> str:
        return self.username or f"User {self.user_id}"


class Deck(models.Model):
    """
    Модель для хранения колоды (кэш).
    Карты хранятся как списки ID в JSON-полях для сохранения дубликатов.
    """
    deck_code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Код колоды"
    )
    owner = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='decks',
        verbose_name="Владелец (кто отправил)"
    )
    character_card_ids = models.JSONField(
        default=list,
        verbose_name="ID карт персонажей"
    )
    action_card_ids = models.JSONField(
        default=list,
        verbose_name="ID карт действий"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата добавления"
    )

    class Meta:
        verbose_name = "Колода"
        verbose_name_plural = "Колоды"
        ordering = ['-created_at']

    @admin.display(description='Владелец')
    def owner_link(self):
        """Ссылка на страницу владельца в админ-панели."""
        if not self.owner:
            return "Нет данных"
        url = (
            f"/admin/users/telegramuser/{self.owner.pk}/change/"
        )
        return format_html('<a href="{}">{}</a>', url, self.owner)

    def __str__(self) -> str:
        return self.deck_code


class UserActivity(models.Model):
    """Модель для логирования действий пользователя."""

    class ActivityType(models.TextChoices):
        MESSAGE_RECEIVED = 'MESSAGE', 'Получено сообщение'
        DECK_PROCESSED = 'DECK_OK', 'Колода обработана'
        INVALID_CODE = 'DECK_FAIL', 'Ошибка обработки колоды'
        EMPTY_REQUEST = 'EMPTY_REQ', 'Пустой запрос'
        COMMAND_USED = 'COMMAND', 'Использована команда'
        ERROR_OCCURRED = 'ERROR', 'Произошла ошибка'

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name="Пользователь"
    )
    activity_type = models.CharField(
        max_length=10,
        choices=ActivityType.choices,
        db_index=True,
        verbose_name="Тип действия"
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Детали"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время действия"
    )

    class Meta:
        verbose_name = "Действие пользователя"
        verbose_name_plural = "Действия пользователей"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.get_activity_type_display()} at {self.created_at:%Y-%m-%d %H:%M}"