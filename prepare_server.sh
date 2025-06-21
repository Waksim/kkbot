#!/bin/bash
# Скрипт для первоначальной настройки сервера под управлением root.
# Он создает нового пользователя, устанавливает Docker и настраивает права.

set -e # Прерывать выполнение при любой ошибке

# --- 1. Создание нового пользователя ---
USERNAME="gitcg"
if id "$USERNAME" &>/dev/null; then
    echo "Пользователь '$USERNAME' уже существует. Пропускаем создание."
else
    echo "Создание пользователя '$USERNAME'..."
    # Создаем пользователя без пароля (вход будет по SSH ключу) и без интерактивных запросов
    adduser --disabled-password --gecos "" $USERNAME
    echo "Добавление пользователя '$USERNAME' в группу sudo..."
    usermod -aG sudo $USERNAME
    echo "Пользователь '$USERNAME' успешно создан."
fi

# --- 2. Обновление системы ---
echo "Обновление списка пакетов и системы..."
apt-get update && apt-get upgrade -y

# --- 3. Установка основных зависимостей ---
echo "Установка Git, Curl..."
apt-get install -y git curl

# --- 4. Установка Docker ---
if ! command -v docker &> /dev/null; then
    echo "Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "Docker успешно установлен."
else
    echo "Docker уже установлен. Пропускаем."
fi

# --- 5. Установка Docker Compose ---
# Docker Compose v2 теперь является плагином для Docker
if ! docker compose version &> /dev/null; then
    echo "Установка Docker Compose..."
    apt-get install -y docker-compose-plugin
    echo "Docker Compose успешно установлен."
else
    echo "Docker Compose уже установлен. Пропускаем."
fi

# --- 6. Настройка прав для Docker ---
echo "Добавление пользователя '$USERNAME' в группу docker..."
usermod -aG docker $USERNAME

# --- 7. Настройка входа для нового пользователя по SSH ---
# Копируем авторизованные ключи root новому пользователю,
# чтобы можно было зайти под ним с тем же SSH-ключом.
mkdir -p /home/$USERNAME/.ssh
cp ~/.ssh/authorized_keys /home/$USERNAME/.ssh/authorized_keys
chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh
chmod 700 /home/$USERNAME/.ssh
chmod 600 /home/$USERNAME/.ssh/authorized_keys

echo "--------------------------------------------------------"
echo "✅ Подготовка сервера завершена!"
echo "Теперь выйдите из сессии root и зайдите под пользователем '$USERNAME'."
echo "Пример: ssh $USERNAME@<your_server_ip>"
echo "После этого выполните шаги из README для настройки проекта."