"""
Настройка логирования
"""
import logging
import sys
from pathlib import Path

import structlog

from app.config import settings


def setup_logging():
    """
    Настраивает логирование для приложения.
    
    В development: цветной вывод в консоль
    В production: JSON формат для сбора логами
    """
    
    # Путь к логам
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Уровень логирования
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Конфигурация structlog
    if settings.is_production:
        # Production: JSON формат
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: цветной вывод в консоль
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=False,
        )
    
    # Настройка стандартного logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Логгер для приложения
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logging configured",
        level=settings.log_level,
        environment=settings.app_env,
        timezone=settings.timezone,
    )
    
    return logger
