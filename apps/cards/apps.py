from django.apps import AppConfig
from django.db.models.signals import post_delete
from django.dispatch import receiver
import logging
import os

logger = logging.getLogger(__name__)


class CardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cards'

    def ready(self):
        """
        Вызывается, когда Django полностью загрузит приложение.
        Идеальное место для подключения сигналов.
        """
        from .models import Card  # Импортируем модель здесь, чтобы избежать циклических импортов

        @receiver(post_delete, sender=Card)
        def delete_card_image_on_delete(sender, instance: Card, **kwargs):
            """
            Сигнал, который срабатывает после удаления объекта Card из БД
            и удаляет связанный с ним файл изображения с диска.
            """
            # `instance` - это удаляемый объект Card, предоставляемый сигналом.
            image_path = instance.local_image_path

            if image_path.exists() and image_path.is_file():
                try:
                    os.remove(image_path)
                    logger.info(f"Успешно удален файл изображения: {image_path}")
                except OSError as e:
                    logger.error(f"Ошибка при удалении файла изображения {image_path}: {e}", exc_info=True)
            else:
                logger.warning(f"Файл изображения для удаленной карты не найден по пути: {image_path}")