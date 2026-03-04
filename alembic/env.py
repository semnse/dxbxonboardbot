from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
import os

# Добавляем корень проекта в PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем настройки и модели
from app.config import settings
from app.database.connection import Base
from app.database.models_bot import User, Subscription, DailyReport

# Alembic Config object
config = context.config

# Переопределяем URL БД из настроек
config.set_main_option("sqlalchemy.url", settings.database_url)

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


def run_migrations_online() -> None:
    """
    Запуск миграций в 'онлайн' режиме (с подключением к БД).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
