# 1. Базовый образ Python 3.13
FROM python:3.13-slim

# 2. Переменные окружения
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Установка системных зависимостей для сборки
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# 4. Установка рабочей директории
WORKDIR /app

# 5. Установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Копирование кода проекта
COPY . .