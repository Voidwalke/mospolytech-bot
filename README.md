# МосПолитех Telegram Бот

Полнофункциональный чат-бот для студентов, преподавателей и администрации Московского Политехнического Университета.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-3.x-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Возможности

### Для студентов
- **FAQ** — База часто задаваемых вопросов с умным поиском
- **Расписание** — Просмотр расписания занятий и экзаменов
- **Документы** — Шаблоны заявлений и справок
- **Обращения** — Система тикетов для связи с деканатом
- **Профиль** — Управление персональными данными

### Для модераторов (деканат)
- Обработка обращений студентов
- Статистика и аналитика
- Ответы на тикеты

### Для администраторов
- Управление FAQ (категории, вопросы)
- Управление пользователями и ролями
- Массовые рассылки
- Расширенная статистика и экспорт

## Быстрый старт

### 1. Клонирование и настройка окружения

```bash
# Клонируем репозиторий
cd "chat bot2"

# Создаём виртуальное окружение
python -m venv venv

# Активируем (Linux/Mac)
source venv/bin/activate

# Активируем (Windows)
venv\Scripts\activate

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Настройка конфигурации

```bash
# Копируем пример конфигурации
cp env.example .env

# Редактируем .env файл
nano .env
```

Основные параметры:
```env
# Обязательно
BOT_TOKEN=your_bot_token_from_@BotFather
ADMIN_IDS=123456789,987654321  # Ваш Telegram ID

# Опционально
DATABASE_URL=sqlite+aiosqlite:///./bot.db
LOG_LEVEL=INFO
```

### 3. Запуск бота

```bash
# Создаём папку для логов
mkdir -p logs

# Запускаем
python bot.py
```

## Структура проекта

```
chat bot2/
├── app/
│   ├── __init__.py
│   ├── config.py              # Конфигурация
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py            # Подключение к БД
│   │   └── models.py          # Модели SQLAlchemy
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py           # Старт и базовые команды
│   │   ├── faq.py             # FAQ и поиск
│   │   ├── tickets.py         # Система тикетов
│   │   ├── profile.py         # Профиль пользователя
│   │   ├── documents.py       # Документы
│   │   ├── schedule.py        # Расписание
│   │   ├── admin.py           # Админ-панель
│   │   └── feedback.py        # Обратная связь
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── main.py            # Главные клавиатуры
│   │   ├── faq.py             # Клавиатуры FAQ
│   │   ├── tickets.py         # Клавиатуры тикетов
│   │   ├── admin.py           # Клавиатуры админки
│   │   └── inline.py          # Общие inline клавиатуры
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── auth.py            # Авторизация
│   │   ├── logging.py         # Логирование
│   │   └── throttling.py      # Антиспам
│   ├── services/
│   │   ├── __init__.py
│   │   ├── faq_service.py     # Сервис FAQ
│   │   ├── ticket_service.py  # Сервис тикетов
│   │   ├── user_service.py    # Сервис пользователей
│   │   ├── document_service.py
│   │   ├── schedule_service.py
│   │   ├── analytics_service.py
│   │   └── notification_service.py
│   └── utils/
│       ├── __init__.py
│       ├── validators.py      # Валидаторы
│       └── formatters.py      # Форматтеры
├── logs/                      # Логи (создаётся автоматически)
├── bot.py                     # Точка входа
├── requirements.txt           # Зависимости
├── env.example               # Пример конфигурации
└── README.md
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота |
| `/help` | Справка |
| `/faq` | База FAQ |
| `/tickets` | Мои обращения |
| `/profile` | Мой профиль |
| `/schedule` | Расписание |
| `/documents` | Документы |
| `/today` | Расписание на сегодня |
| `/tomorrow` | Расписание на завтра |
| `/exams` | Расписание экзаменов |
| `/feedback` | Обратная связь |
| `/admin` | Админ-панель (только для админов) |

## Роли и доступ

| Роль | Описание | Возможности |
|------|----------|-------------|
| `student` | Студент | FAQ, тикеты, расписание, документы |
| `teacher` | Преподаватель | То же + ответы на тикеты |
| `moderator` | Модератор (деканат) | То же + обработка всех тикетов, статистика |
| `admin` | Администратор | Полный доступ ко всем функциям |

## База данных

Бот использует SQLAlchemy с поддержкой:
- **SQLite** (по умолчанию) — для разработки и небольших установок
- **PostgreSQL** — для продакшена

### Переключение на PostgreSQL

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mospolytech_bot
```

### Модели данных

- **User** — Пользователи с профилями и ролями
- **FAQCategory** — Категории FAQ
- **FAQItem** — Вопросы и ответы
- **Ticket** — Обращения/тикеты
- **TicketMessage** — Сообщения в тикетах
- **Document** — Документы и шаблоны
- **Schedule** — Расписание и события
- **RequestLog** — Логи запросов
- **Feedback** — Обратная связь
- **Notification** — Уведомления

## Аналитика

Бот собирает статистику:
- Количество запросов по типам
- Популярные вопросы FAQ
- Среднее время ответа
- Активность пользователей

Экспорт в Excel доступен из админ-панели.

## Разработка

### Добавление нового хендлера

1. Создайте файл в `app/handlers/`
2. Создайте `Router` и хендлеры
3. Зарегистрируйте роутер в `app/handlers/__init__.py`

```python
from aiogram import Router

router = Router(name="my_handler")

@router.message(F.text == "Моя команда")
async def my_handler(message: Message, user: User):
    await message.answer("Привет!")
```

### Добавление новой модели

1. Добавьте класс модели в `app/database/models.py`
2. Добавьте в `__init__.py`
3. Перезапустите бот (таблицы создадутся автоматически)

## Docker (опционально)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  bot:
    build: .
    env_file: .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./bot.db:/app/bot.db
```

## Поддержка

- Telegram: [@mospolytech_support](https://t.me/mospolytech_support)
- Email: support@mospolytech.ru
- Сайт: [mospolytech.ru](https://mospolytech.ru)

## Лицензия

MIT License — свободно используйте и модифицируйте код.

---

<p align="center">
  <b>Московский Политехнический Университет</b><br>
  <a href="https://mospolytech.ru">mospolytech.ru</a>
</p>
