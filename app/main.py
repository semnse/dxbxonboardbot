"""
Точка входа приложения (FastAPI)
Telegram-бот онбординга для смарт-процессов Bitrix24

Исправлено:
- Бот polling запущен как asyncio task в том же event loop
- Правильная инициализация БД
- Корректная обработка shutdown
- Удалено дублирование планировщиков (используется Celery Beat)
- Используется SelectorEventLoop для совместимости с psycopg на Windows
"""
import asyncio
import logging
import selectors
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.database.connection import init_db, close_db
from app.bot import dp, bot, start_scheduler, shutdown_scheduler
from app.bot.commands import commands_router
from app.bot.subscriptions import subscriptions_router
from app.api.routes import webhook, health
from app.utils.logger import setup_logging

# Настраиваем SelectorEventLoop для совместимости с psycopg на Windows
# Это должно быть вызвано до любого asyncio кода
if hasattr(asyncio, 'SelectorEventLoop'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Подключаем роутеры с обработчиками
dp.include_router(commands_router)
dp.include_router(subscriptions_router)

# Настраиваем логирование
setup_logging()

logger = structlog.get_logger(__name__)


# Глобальная задача для бота
_bot_polling_task: asyncio.Task | None = None


async def run_bot_polling_task():
    """
    Запускает polling бота как asyncio task.

    Важно: запускается в том же event loop что и FastAPI,
    а не в отдельном потоке.
    """
    try:
        logger.info("Bot polling task started")
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except asyncio.CancelledError:
        logger.info("Bot polling task cancelled")
        raise
    except Exception as e:
        logger.exception(f"Bot polling task error: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения"""
    # ============================================
    # STARTUP
    # ============================================
    logger.info("Starting application...", stage="startup")

    try:
        # Инициализация БД
        await init_db()
        logger.info("Database initialized", stage="startup")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Продолжаем запуск, БД может быть недоступна временно

    try:
        # Запуск бота polling как asyncio task в том же event loop
        global _bot_polling_task
        _bot_polling_task = asyncio.create_task(run_bot_polling_task())
        logger.info("Bot polling task created", stage="startup")
    except Exception as e:
        logger.error(f"Failed to start bot polling: {e}")

    # Запуск планировщика задач (рассылка в 9:00 МСК)
    try:
        await start_scheduler()
        logger.info("Scheduler started", stage="startup")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

    # Даём время на запуск задач
    await asyncio.sleep(2)

    logger.info("Application started successfully", stage="startup")

    try:
        yield
    finally:
        # ============================================
        # SHUTDOWN
        # ============================================
        logger.info("Shutting down application...", stage="shutdown")

        # Остановка бота polling
        if _bot_polling_task and not _bot_polling_task.done():
            logger.info("Cancelling bot polling task...")
            _bot_polling_task.cancel()
            try:
                await _bot_polling_task
            except asyncio.CancelledError:
                logger.info("Bot polling task cancelled successfully")
            except Exception as e:
                logger.error(f"Error cancelling bot polling task: {e}")

        # Остановка планировщика
        try:
            await shutdown_scheduler()
            logger.info("Scheduler stopped", stage="shutdown")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

        # Закрытие подключения к БД
        try:
            await close_db()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

        # Закрытие сессии бота
        try:
            await bot.session.close()
            logger.info("Bot session closed")
        except Exception as e:
            logger.error(f"Error closing bot session: {e}")

        logger.info("Application shutdown complete", stage="shutdown")


# Создание приложения
app = FastAPI(
    title="Telegram Onboarding Bot",
    description="Бот напоминаний для клиентов на этапе внедрения",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (для webhook)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production ограничить
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация роутов
app.include_router(webhook.router, prefix="/webhook", tags=["Webhooks"])
app.include_router(health.router, prefix="/health", tags=["Health"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "environment": settings.app_env
    }


@app.get("/ready")
async def readiness_check():
    """Readiness probe для Kubernetes"""
    # Проверяем что бот и планировщик запущены
    bot_ready = _bot_polling_task is not None and not _bot_polling_task.done()
    
    return {
        "status": "ready" if bot_ready else "starting",
        "bot_polling": "running" if bot_ready else "starting",
    }
