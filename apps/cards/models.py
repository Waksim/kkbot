from django.db import models
from django.conf import settings
from pathlib import Path

class Tag(models.Model):
    """Модель для тегов карт (Элемент, Оружие, Регион и т.д.)."""
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Название тега"
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

class Card(models.Model):
    """Основная модель для игровой карты."""
    class CardType(models.TextChoices):
        CHARACTER = 'Character', 'Персонаж'
        ACTION = 'Action', 'Действие'

    card_id = models.PositiveIntegerField(
        primary_key=True,
        verbose_name="ID карты"
    )
    card_type = models.CharField(
        max_length=10,
        choices=CardType.choices,
        db_index=True,
        verbose_name="Тип карты"
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="Название"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Подзаголовок"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    cost_info = models.JSONField(
        default=list,
        verbose_name="Информация о стоимости"
    )
    hp = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Здоровье"
    )
    related_card = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='character_card',
        verbose_name="Связанная карта таланта/персонажа"
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='cards',
        blank=True,
        verbose_name="Теги"
    )
    is_new = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Новая карта (еще не в релизе)"
    )

    class Meta:
        verbose_name = "Карта"
        verbose_name_plural = "Карты"
        ordering = ['card_id']

    @property
    def local_image_path(self) -> Path:
        """Свойство для получения локального пути к изображению."""
        return settings.MEDIA_ROOT / 'card_images' / f"{self.card_id}.webp"

    def __str__(self) -> str:
        return f"{self.name} ({self.card_id})"