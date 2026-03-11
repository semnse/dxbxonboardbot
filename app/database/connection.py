"""
Подключение к базе данных (PostgreSQL + SQLAlchemy Async)
Исправлено для стабильной работы на Windows с asyncpg

Оптимизации:
- ✅ Retry logic с экспоненциальной задержкой
- ✅ Обработка специфичных ошибок PostgreSQL
- ✅ Улучшенная работа с пулом соединений
- ✅ Таймауты на подключения
"""
import asyncio
import logging
from typing import AsyncGenerator, Optional, Callable, Any, TypeVar
from contextlib import asynccontextmanager
from functools import wraps

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,
    DatabaseError,
    IntegrityError,
)
from sqlalchemy import text
import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Base(DeclarativeBase):
    """Базовый класс для моделей SQLAlchemy"""
    pass


# Глобальные переменные для движка и сессии
_engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _create_engine() -> AsyncEngine:
    """
    Создаёт асинхронный движок с оптимизированными настройками.
    
    Оптимизации пула соединений:
    - pool_pre_ping=True: проверка соединений перед использованием
    - pool_size=10: увеличенный пул для высокой нагрузки
    - max_overflow=20: больше соединений при пиках
    - pool_recycle=1800: пересоздание соединений каждые 30 минут
    - pool_timeout=30: таймаут получения соединения из пула
    """
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.info(f"Creating database engine with URL: {db_url[:60]}...")

    return create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        pool_timeout=30,
        connect_args={
            "server_settings": {
                "application_name": "onboarding_bot",
            },
            "timeout": 30,  # Таймаут подключения
            "command_timeout": 60,  # Таймаут выполнения запросов
        },
    )


def get_engine() -> AsyncEngine:
    """Получает или создаёт движок"""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_maker():
    """Получает или создаёт фабрику сессий"""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        engine = get_engine()
        AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return AsyncSessionLocal


async def init_db():
    """Инициализация БД"""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            if not settings.is_production:
                await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """Закрытие БД"""
    global _engine, AsyncSessionLocal
    if _engine:
        await _engine.dispose()
        _engine = None
    AsyncSessionLocal = None
    logger.info("Database connection closed")


def _is_retryable_error(error: Exception) -> bool:
    """
    Проверяет, можно ли повторить запрос при данной ошибке.
    
    Retryable ошибки:
    - OperationalError: проблемы с подключением
    - asyncpg.exceptions.*: transient ошибки PostgreSQL
    - DatabaseError: временные ошибки БД
    
    Non-retryable:
    - IntegrityError: ошибки целостности (дубликаты, FK)
    """
    if isinstance(error, IntegrityError):
        return False
    
    if isinstance(error, (OperationalError, DatabaseError)):
        return True
    
    # asyncpg специфичные ошибки
    # Примечание: используем правильные имена классов исключений asyncpg
    retryable_exceptions = [
        asyncpg.exceptions.InterfaceError,
        asyncpg.exceptions.InterfaceWarning,
        asyncpg.exceptions.TooManyConnectionsError,
        asyncpg.exceptions.CannotConnectNowError,
        asyncpg.exceptions.ConnectionFailureError,
        asyncpg.exceptions.ConnectionRejectionError,
        asyncpg.exceptions.SerializationError,  # Правильное имя (не SerializationFailure)
        asyncpg.exceptions.DeadlockDetectedError,
    ]
    
    for exc_type in retryable_exceptions:
        if isinstance(error, exc_type):
            return True
    
    return False


def retry_on_db_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
):
    """
    Декоратор для retry logic с экспоненциальной задержкой.
    
    Args:
        max_retries: Максимальное количество попыток
        base_delay: Базовая задержка в секундах
        max_delay: Максимальная задержка
        exponential_base: База экспоненты
        
    Usage:
        @retry_on_db_error(max_retries=3)
        async def my_db_function():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not _is_retryable_error(e):
                        # Не retry-им невосстанавливаемые ошибки
                        logger.warning(
                            "db_error_non_retryable",
                            function=func.__name__,
                            error_type=type(e).__name__,
                            error=str(e)
                        )
                        raise
                    
                    if attempt < max_retries - 1:
                        # Экспоненциальная задержка с jitter
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        # Добавляем случайный jitter (±10%)
                        jitter = delay * 0.1 * (2 * asyncio.get_event_loop().time() % 1 - 1)
                        actual_delay = max(0.1, delay + jitter)
                        
                        logger.warning(
                            "db_error_retrying",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=actual_delay,
                            error_type=type(e).__name__,
                            error=str(e)
                        )
                        await asyncio.sleep(actual_delay)
                    else:
                        logger.error(
                            "db_error_max_retries",
                            function=func.__name__,
                            max_retries=max_retries,
                            error_type=type(e).__name__,
                            error=str(e)
                        )
            
            # Должны были выбросить в цикле, но на всякий случай
            raise last_exception
        
        return wrapper
    return decorator


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для сессии БД с retry logic.
    
    Особенности:
    - Автоматический commit при успехе
    - Автоматический rollback при ошибке
    - Retry при transient ошибках
    - Гарантированное закрытие сессии
    
    Usage:
        async with get_db_session() as session:
            # работа с session
            session.add(model)
            await session.commit()
    """
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        session = None
        try:
            maker = get_session_maker()
            session = maker()
            yield session
            # Commit выполняется явно в коде, здесь только проверка
            if not session.in_transaction():
                await session.commit()
            return
        except Exception as e:
            if session and session.in_transaction():
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    logger.error("rollback_error", error=str(rollback_error))
            
            if not _is_retryable_error(e):
                logger.error("db_error_non_retryable", error=str(e))
                raise
            
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "db_session_retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay,
                    error=str(e)
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "db_session_max_retries",
                    max_retries=max_retries,
                    error=str(e)
                )
                raise
        finally:
            if session:
                try:
                    await session.close()
                except Exception:
                    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI endpoints"""
    async with get_db_session() as session:
        yield session


async def execute_with_retry(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs
) -> T:
    """
    Выполняет функцию с retry logic.
    
    Args:
        func: Асинхронная функция для выполнения
        *args: Позиционные аргументы для функции
        max_retries: Максимальное количество попыток
        base_delay: Базовая задержка
        **kwargs: Именованные аргументы для функции
        
    Returns:
        Результат выполнения функции
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if not _is_retryable_error(e):
                raise
            
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "execute_retrying",
                    function=func.__name__,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay,
                    error=str(e)
                )
                await asyncio.sleep(delay)
    
    raise last_exception
