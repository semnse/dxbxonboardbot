"""
Подключение к базе данных (PostgreSQL + SQLAlchemy Async)
Исправлено для стабильной работы на Windows с asyncpg
"""
import asyncio
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Базовый класс для моделей SQLAlchemy"""
    pass


# Глобальные переменные для движка и сессии
_engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None


def _create_engine() -> AsyncEngine:
    """
    Создаёт асинхронный движок с оптимизированными настройками для Windows.
    """
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    logger.info(f"Creating database engine with URL: {db_url[:60]}...")
    
    return create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
        pool_timeout=60,
        connect_args={
            "server_settings": {
                "application_name": "onboarding_bot",
            },
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


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для сессии БД с retry logic.
    
    Usage:
        async with get_db_session() as session:
            # работа с session
    """
    max_retries = 3
    
    for attempt in range(max_retries):
        session = None
        try:
            maker = get_session_maker()
            session = maker()
            yield session
            try:
                await session.commit()
            except:
                pass
            return
        except Exception as e:
            logger.warning(f"Database error (attempt {attempt + 1}/{max_retries}): {e}")
            if session:
                try:
                    await session.rollback()
                except:
                    pass
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))
            else:
                logger.error(f"Database error after {max_retries} attempts: {e}")
                raise
        finally:
            if session:
                try:
                    await session.close()
                except:
                    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI endpoints"""
    async with get_db_session() as session:
        yield session
