# МосПолитех Telegram Бот
# Dockerfile для production деплоя

FROM python:3.11-slim

# Метаданные
LABEL maintainer="MosPolytech IT"
LABEL description="Telegram Bot for Moscow Polytechnic University"

# Переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Рабочая директория
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаём директорию для логов
RUN mkdir -p /app/logs

# Создаём непривилегированного пользователя
RUN adduser --disabled-password --gecos '' botuser && \
    chown -R botuser:botuser /app

USER botuser

# Запуск
CMD ["python", "bot.py"]

