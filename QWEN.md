# Telegram Onboarding Bot — Контекст проекта

## 📋 Обзор проекта

**Telegram-бот онбординга** — это система напоминаний для клиентов на этапе внедрения продуктов DocsInBox. Бот интегрируется с **Bitrix24** (смарт-процесс "Торговые точки", ID 1070) и отправляет персонализированные отчёты в Telegram-чаты.

### Основное назначение
- Ежедневные напоминания клиентам о шагах внедрения (в 9:00 МСК)
- Отслеживание сделок на стадии "Ждём действий клиента"
- Привязка Bitrix-карточек к Telegram-чатом через команду `/add`
- Формирование отчётов с рисками и рекомендациями

### Ключевые функции
- **Polling Bitrix24**: Получение активных сделок с полной пагинацией (591+ карточек)
- **Telegram-бот**: Команды `/start`, `/add`, `/report`, `/help`
- **Планировщик (APScheduler)**: Ежедневная рассылка и синхронизация с БД
- **FastAPI вебхуки**: Endpoints для интеграции с Bitrix24

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI (main.py)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Bot Polling │  │ Scheduler    │  │ Webhook Endpoints  │  │
│  │ (aiogram)   │  │ (APScheduler)│  │ (/webhook/bitrix)  │  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Bitrix24 API    │  │ PostgreSQL      │  │ Telegram API    │
│ (aiohttp)       │  │ (asyncpg)       │  │ (aiogram)       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Структура проекта

```
E:\Carrot1_WaitingClient\
├── app/
│   ├── main.py              # Точка входа (FastAPI + bot + scheduler)
│   ├── config.py            # Настройки (pydantic-settings)
│   ├── api/
│   │   ├── routes/
│   │   │   ├── webhook.py   # Bitrix webhook handler
│   │   │   └── health.py    # Health check endpoints
│   │   └── schemas/         # Pydantic модели для API
│   ├── bot/
│   │   ├── commands.py      # Обработчики команд (/start, /add, /report, /help)
│   │   ├── scheduler.py     # APScheduler задачи (рассылка, синхронизация)
│   │   ├── message_builder.py # Построитель сообщений
│   │   └── telegram_service.py # Сервис для отправки сообщений
│   ├── database/
│   │   ├── connection.py    # SQLAlchemy async engine & session
│   │   ├── models.py        # ORM модели
│   │   ├── repository.py    # Репозитории для работы с БД
│   │   └── db_sync.py       # Синхронные утилиты БД
│   ├── services/
│   │   ├── bitrix_polling_service.py  # Опрос Bitrix24 с пагинацией
│   │   ├── bitrix_service.py          # Базовый Bitrix клиент
│   │   ├── bitrix_stage_service.py    # Работа со стадиями сделок
│   │   ├── wait_reasons_service.py    # Форматирование причин ожидания
│   │   ├── telegram_service.py        # Telegram API клиент
│   │   └── notification_service.py    # Уведомления
│   └── utils/
│       └── logger.py        # Настройка structlog
├── tests/
│   ├── simple_test.py       # Базовые тесты (config, message builder)
│   └── full_system_test.py  # Комплексное тестирование
├── tools/
│   ├── test_bitrix_integration.py  # Скрипт тестирования интеграции
│   └── ngrok.exe                   # ngrok для туннелирования
├── migrations/              # Миграции БД (Alembic или ручные)
├── docs/                    # Документация
├── ssl/                     # SSL сертификаты
├── logs/                    # Логи приложения
├── init.sql                 # Инициализация БД (таблицы + справочники)
├── .env.example             # Шаблон переменных окружения
└── venv/                    # Python virtual environment
```

---

## 🚀 Запуск и разработка

### Предварительные требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.10+ | Требуется для type hints (`asyncio.Task | None`) |
| PostgreSQL | 15+ | Контейнер Docker или локальная установка |
| Docker Desktop | — | Для запуска PostgreSQL в контейнере |
| ngrok | — | Для туннелирования webhook |

### 1. Создание базы данных

```bash
# Создать БД
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE onboarding_bot;"

# Инициализировать таблицы
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d onboarding_bot -f init.sql
```

### 2. Настройка окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
# .env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
BITRIX_WEBHOOK_URL=https://your-portal.bitrix24.ru/rest/1/YOUR_CODE/
DATABASE_URL=postgresql://bot_user:password@localhost:5432/onboarding_bot
APP_ENV=development
TIMEZONE=Europe/Moscow
LOG_LEVEL=DEBUG
```

### 3. Запуск приложения

```bash
# Активировать venv
venv\Scripts\activate

# Запустить FastAPI + bot + scheduler
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Настройка ngrok (для webhook)

```bash
# В новом окне PowerShell
cd E:\Carrot1_WaitingClient\tools
.\ngrok.exe config add-authtoken ВАШ_ТОКЕН
.\ngrok.exe http 8000
```

Скопируйте HTTPS URL (например, `https://abc123.ngrok.io`) и настройте webhook в Bitrix24:
- **URL:** `https://YOUR_NGROK_URL.ngrok.io/webhook/bitrix/smart`
- **Событие:** `ONCRMDYNAMICITEMUPDATE`

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Простой тест (config, message builder, Telegram token)
python -m pytest tests/simple_test.py -v

# Комплексный тест
python -m pytest tests/full_system_test.py -v

# Тест интеграции с Bitrix24
python tools/test_bitrix_integration.py
```

### Проверка здоровья

```bash
# Health check
curl http://localhost:8000/

# Database health
curl http://localhost:8000/health/db

# Full health
curl http://localhost:8000/health/full

# Test Bitrix integration
curl http://localhost:8000/health/test-bitrix/1070
```

---

## 📊 База данных

### Основные таблицы

| Таблица | Описание |
|---------|----------|
| `clients` | Клиенты (торговые точки), привязка к Bitrix deal ID |
| `products` | Справочник продуктов (ЕГАИС, Меркурий, Маркировка, ЮЗЭДО) |
| `product_features` | Функции продуктов (что доступно при покупке) |
| `client_products` | Связь клиент-продукты (что купил клиент) |
| `wait_reasons` | Словарь причин ожидания (нет УКЭП, нет JaCarta, и т.д.) |
| `risk_messages` | Маппинг Причина → Текст риска |
| `deal_stages` | Стадии сделок Bitrix24 |
| `deal_states` | Текущие состояния сделок (активность бота, счётчики) |
| `message_logs` | Логи отправленных сообщений |
| `chat_bindings` | Привязки Telegram-чатов к Bitrix-карточкам |
| `bot_settings` | Настройки бота (время отправки, часовой пояс) |

### Справочники (заполняются при инициализации)

- **Продукты:** 4 продукта (ЕГАИС, Меркурий, Маркировка, ЮЗЭДО)
- **Причины ожидания:** 8 причин (нет УКЭП, нет JaCarta, и т.д.)
- **Стадии сделок:** 3 стадии (ЖДЁМ_ДЕЙСТВИЙ_КЛИЕНТА, УСПЕШНО, ПРОВАЛ)

---

## 🔧 Ключевые компоненты

### 1. BitrixPollingService (`app/services/bitrix_polling_service.py`)

Опрос смарт-процесса "Торговые точки" (ID 1070, воронка 38).

**Особенности:**
- Полная пагинация (возвращает 591+ карточек)
- Retry-логика для transient-ошибок
- Обработка UF-полей (продукты, причины ожидания, Telegram)

**Стадии ожидания:**
```python
wait_stage_ids = [
    "DT1070_38:UC_70SK2H",  # Чек работы системы
    "DT1070_38:UC_B7P2X4",  # Выведена на MRR
    "DT1070_38:UC_ILDKHV",  # Ждём действий клиента
    # ... ещё 7 стадий
]
```

### 2. Scheduler (`app/bot/scheduler.py`)

Две периодические задачи:

| Задача | Расписание | Описание |
|--------|------------|----------|
| `send_daily_reminders` | 9:00 МСК | Отправка напоминаний активным клиентам |
| `sync_with_bitrix` | 3:00 МСК | Синхронизация БД с Bitrix24 |

### 3. Telegram Commands (`app/bot/commands.py`)

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие, инструкция |
| `/add <ID>` | Привязка Bitrix-карточки к чату |
| `/report` | Получение текущего отчёта |
| `/help` | Справка по командам |

### 4. FastAPI Endpoints (`app/api/routes/`)

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Health check |
| `/health/db` | GET | Проверка подключения к БД |
| `/health/full` | GET | Полная проверка здоровья |
| `/health/test-bitrix/{item_id}` | GET | Тест интеграции с Bitrix |
| `/webhook/bitrix/smart` | POST | Webhook от Bitrix24 |

---

## 🛠 Зависимости

Основные библиотеки (определяются по импортам в коде):

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
aiogram>=3.0.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.28.0
pydantic-settings>=2.0.0
apscheduler>=3.10.0
structlog>=23.0.0
aiohttp>=3.8.0
python-dotenv>=1.0.0
pytest>=7.0.0
```

---

## 📝 Конвенции разработки

### Стиль кода
- **Type hints:** Обязательны для всех функций (Python 3.10+ синтаксис)
- **Логирование:** Используется `structlog` для структурированного логирования
- **Асинхронность:** Весь I/O код асинхронный (asyncio, asyncpg, aiohttp)

### Структура коммитов
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Примеры типов: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Тестирование
- Модульные тесты в `tests/`
- Интеграционные скрипты в `tools/`
- Запуск через `pytest -v`

---

## 🔍 Поиск и устранение неисправностей

### Бот не запускается
```bash
# Проверка импортов
python -c "from app.main import app; print('OK')"

# Проверка путей
python -c "import sys; print(sys.path)"
```

### Ошибка подключения к БД
```bash
# Проверка контейнера PostgreSQL
docker ps | grep onboarding_postgres

# Проверка подключения
docker exec -i onboarding_postgres psql -U postgres -d onboarding_bot -c "SELECT 1"
```

### Webhook не работает
1. Проверьте ngrok: `.\ngrok.exe http 8000`
2. Скопируйте HTTPS URL
3. Настройте webhook в Bitrix24
4. Проверьте логи uvicorn

---

## 📚 Дополнительные ресурсы

- **Полная документация:** `docs/` (папка пуста, требует заполнения)
- **Статус запуска:** `STATUS.md` (текущее состояние развёртывания)
- **Пример .env:** `.env.example`

---

## 🎯 Следующие шаги для разработки

1. **Добавить зависимости:** Создать `requirements.txt` или `pyproject.toml`
2. **Заполнить документацию:** Добавить детали в `docs/`
3. **Настроить CI/CD:** Добавить GitHub Actions или другой CI
4. **Расширить тесты:** Покрыть сервисы и репозитории тестами
5. **Миграции БД:** Настроить Alembic для управления миграциями
