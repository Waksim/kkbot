import os
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Создает суперпользователя, если он еще не существует.

    Эта команда предназначена для автоматического создания администратора
    в средах разработки и CI/CD. Она считывает учетные данные из
    переменных окружения:
    - ADMIN_USERNAME
    - ADMIN_PASSWORD
    - ADMIN_EMAIL

    Команда является идемпотентной: при повторном запуске, если
    пользователь с таким именем уже существует, она ничего не делает.
    """
    help = "Создает суперпользователя из переменных окружения, если он не существует."

    def handle(self, *args: Any, **options: Any) -> None:
        """Основная логика команды."""
        User = get_user_model()
        username = os.getenv('ADMIN_USERNAME')
        password = os.getenv('ADMIN_PASSWORD')
        email = os.getenv('ADMIN_EMAIL')

        if not all([username, password, email]):
            self.stdout.write(self.style.WARNING(
                "Пропущено создание суперпользователя: не заданы переменные "
                "ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL."
            ))
            return

        if not User.objects.filter(username=username).exists():
            self.stdout.write(f"Создание суперпользователя '{username}'...")
            try:
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Суперпользователь '{username}' успешно создан."
                ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(
                    f"Ошибка при создании суперпользователя: {e}"
                ))
        else:
            self.stdout.write(self.style.NOTICE(
                f"Суперпользователь '{username}' уже существует. Создание пропущено."
            ))