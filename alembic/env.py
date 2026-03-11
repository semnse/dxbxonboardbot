from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, AsyncEngine

from alembic import context

import sys
import os

# Добавляем корень проекта в PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем настройки и модели
from app.config import settings
from app.database.connection import Base

# Импортируем ВСЕ модели для корректной авто-генерации миграций
from app.database.models_bot import User, Subscription, DailyReport
from app.database.models import (
    Client, Product, ClientProduct, DealState, DealStage,
    MessageLog, WaitReason, RiskMessage, ProductFeature,
    BotSetting, ChatBinding
)

# Alembic Config object
config = context.config

# Переопределяем URL БД из настроек
db_url = settings.database_url
# Преобразуем URL в asyncpg формат для Alembic
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
config.set_main_option("sqlalchemy.url", db_url)

# Target metadata для авто-генерации миграций
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Запуск миграций в 'оффлайн' режиме (без подключения к БД).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Выполняет миграции с переданным соединением"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запуск миграций в асинхронном режиме"""
    connectable: AsyncEngine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Запуск миграций в 'онлайн' режиме (с подключением к БД).
    Асинхронная версия для asyncpg.
    """
    import asyncio
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
