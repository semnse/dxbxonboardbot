# Telegram Onboarding Bot + Bitrix24 Status Tracker

Бот для напоминания клиентам о необходимых действиях на этапе внедрения. Интегрируется с Bitrix24 и Telegram.

## 📋 Возможности

### Основной функционал
- ✅ Ежедневные напоминания о шагах внедрения (9:00 МСК)
- ✅ Отслеживание сделок на стадии "Ждём действий клиента"
- ✅ Привязка Bitrix-карточек к Telegram-чатом через `/add`
- ✅ Формирование отчётов с рисками и рекомендациями

### Новый функционал (Celery + Redis)
- ✅ Подписка на карточки Bitrix24 через `/add <ID>`
- ✅ Ежедневная рассылка статусов в 09:00 МСК
- ✅ Ручной запрос статусов (`/status`)
- ✅ Управление подписками (`/list`, `/remove`, `/stop`)
- ✅ Rate limiting для Bitrix API (2 запроса/сек)
- ✅ Кэширование данных в Redis на 24 часа
- ✅ Защита от Telegram Flood Wait

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI + aiogram (bot)                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Webhook     │  │ Commands     │  │ Subscriptions      │  │
│  │ Handler     │  │ (/start)     │  │ (/add, /list)      │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Bitrix24 API    │  │ PostgreSQL      │  │ Redis Cache     │
│ (aiohttp)       │  │ (asyncpg)       │  │ (daily reports) │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         ▲                    ▲
         │                    │
┌─────────────────────────────────────────────────────────────┐
│              Celery Worker + Beat (scheduler)                │
│  ┌─────────────────────────┐  ┌───────────────────────────┐ │
│  │ fetch_daily_statuses    │  │ send_daily_reports        │ │
│  │ 08:00 MSK               │  │ 09:00 MSK                 │ │
│  └─────────────────────────┘  └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Быстрый старт

### Вариант 1: Docker Compose (рекомендуется)

```bash
# 1. Настройте .env
cp .env.example .env
# Заполните переменные окружения

# 2. Запустите все сервисы
docker compose up -d --build

# 3. Примените миграции
docker compose exec bot alembic upgrade head

# 4. Проверьте логи
docker compose logs -f
```

### Вариант 2: Локальная разработка

```bash
# 1. Создайте базу данных
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE onboarding_bot;"
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d onboarding_bot -f init.sql

# 2. Установите зависимости
pip install -r requirements.txt

# 3. Настройте .env
# Заполните переменные окружения

# 4. Запустите приложение
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. В отдельном терминале запустите Celery воркер
celery -A app.celery_app worker --loglevel=info

# 6. В ещё одном терминале запустите планировщик
celery -A app.celery_app beat --loglevel=info
```

## 📁 Структура проекта

```
E:\Carrot1_WaitingClient\
├── app/
│   ├── main.py              # Точка входа (FastAPI + bot)
│   ├── config.py            # Настройки (pydantic-settings)
│   ├── celery_app.py        # Celery приложение + расписание
│   ├── api/
│   │   ├── routes/
│   │   │   ├── webhook.py   # Bitrix webhook handler
│   │   │   └── health.py    # Health check endpoints
│   │   └── schemas/         # Pydantic модели для API
│   ├── bot/
│   │   ├── commands.py      # Обработчики команд (/start, /help)
│   │   ├── subscriptions.py # Новые команды (/add, /list, /remove, /status, /stop)
│   │   └── scheduler.py     # APScheduler задачи
│   ├── database/
│   │   ├── connection.py    # SQLAlchemy async engine
│   │   ├── models.py        # ORM модели (существующие)
│   │   └── models_bot.py    # Новые ORM модели (User, Subscription, DailyReport)
│   ├── tasks/
│   │   ├── fetch_task.py    # Задача сбора статусов (08:00 MSK)
│   │   └── send_task.py     # Задача отправки отчётов (09:00 MSK)
│   └── services/
│       ├── bitrix_service.py        # Bitrix24 API клиент
│       └── telegram_service.py      # Telegram API клиент
├── alembic/                 # Миграции БД
│   ├── versions/
│   │   └── 001_bot_tables.py
│   └── env.py
├── nginx/
│   └── nginx.conf           # Nginx конфигурация
├── ssl/                     # SSL сертификаты
├── tools/
│   └── ngrok.exe            # ngrok для туннелирования
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.worker
├── requirements.txt
└── init.sql
```

## 📊 База данных

### Новые таблицы

| Таблица | Описание |
|---------|----------|
| `bot_users` | Пользователи Telegram |
| `bot_subscriptions` | Подписки на карточки Bitrix24 |
| `bot_daily_reports` | Лог отправки ежедневных отчётов |

### Миграции

```bash
# Применить все миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Показать историю
alembic history
```

## 🎯 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/help` | Справка по командам |
| `/add <ID>` | Добавить карточку Bitrix24 |
| `/list` | Список подписок |
| `/remove <ID>` | Удалить подписку |
| `/status` | Запросить актуальные статусы |
| `/stop` | Отключить рассылку |
| `/report` | Получение текущего отчёта (существующая) |

## ⚙️ Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | — |
| `BOT_WEBHOOK_URL` | URL webhook | — |
| `BOT_SECRET_TOKEN` | Секрет webhook | — |
| `BITRIX_WEBHOOK_URL` | URL вебхука Bitrix24 | — |
| `BITRIX_DOMAIN` | Домен Bitrix24 | — |
| `BITRIX_WEBHOOK_KEY` | Ключ вебхука | — |
| `DATABASE_URL` | PostgreSQL URL | — |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `TIMEZONE` | Часовой пояс | `Europe/Moscow` |
| `MAX_SUBSCRIPTIONS_PER_USER` | Лимит подписок | `5` |

## 🧪 Тестирование

```bash
# Запуск простого теста
python -m pytest tests/simple_test.py -v

# Запуск комплексного теста
python -m pytest tests/full_system_test.py -v

# Запуск теста интеграции с Bitrix24
python tools/test_bitrix_integration.py
```

## 🔧 Полезные команды

### Docker

```bash
# Статус сервисов
docker compose ps

# Логи
docker compose logs -f bot
docker compose logs -f worker
docker compose logs -f beat

# Перезапуск
docker compose restart

# Остановка
docker compose stop

# Полная очистка
docker compose down -v
```

### Celery

```bash
# Запуск воркера
celery -A app.celery_app worker --loglevel=info

# Запуск планировщика
celery -A app.celery_app beat --loglevel=info

# Запуск задачи вручную
celery -A app.celery_app call app.tasks.fetch_task.fetch_daily_statuses
celery -A app.celery_app call app.tasks.send_task.send_daily_reports
```

## 📚 Дополнительные ресурсы

- [aiogram 3.x документация](https://docs.aiogram.dev/)
- [Celery документация](https://docs.celeryq.dev/)
- [Bitrix24 REST API](https://dev.bitrix24.ru/)
- [FastAPI документация](https://fastapi.tiangolo.com/)
- [Alembic документация](https://alembic.sqlalchemy.org/)
