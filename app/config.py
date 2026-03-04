"""
Конфигурация приложения
Исправлено для корректной загрузки .env перед созданием Settings
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Настраиваем базовое логирование до загрузки настроек
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Находим .env файл (ищем от корня проекта)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# Загружаем .env вручную через load_dotenv ПЕРЕД созданием Settings
# Это критически важно для корректной работы
if ENV_FILE.exists():
    logger.info(f"Loading .env from {ENV_FILE}")
    load_dotenv(str(ENV_FILE), override=True)
else:
    logger.warning(f".env file not found at {ENV_FILE}, using environment variables only")


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""

    model_config = SettingsConfigDict(
        env_file=None,  # Используем os.environ (уже загружен через load_dotenv)
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ============================================
    # TELEGRAM
    # ============================================
    telegram_bot_token: str = ""
    
    # Webhook настройки для Telegram
    bot_webhook_url: str = ""
    bot_secret_token: str = ""

    # ============================================
    # BITRIX24
    # ============================================
    bitrix_webhook_url: Optional[str] = None
    bitrix_webhook_secret: Optional[str] = None
    bitrix_oauth_client_id: Optional[str] = None
    bitrix_oauth_client_secret: Optional[str] = None
    bitrix_oauth_access_token: Optional[str] = None
    
    # Настройки для Celery задач
    bitrix_domain: Optional[str] = None
    bitrix_webhook_key: Optional[str] = None

    # ============================================
    # DATABASE & REDIS
    # ============================================
    database_url: str = "postgresql://bot_user:password@localhost:5432/onboarding_bot"
    redis_url: str = "redis://localhost:6379/0"

    # ============================================
    # APPLICATION
    # ============================================
    app_env: str = "development"
    timezone: str = "Europe/Moscow"
    log_level: str = "INFO"

    # ============================================
    # BOT SETTINGS
    # ============================================
    bot_send_time_hour: int = 9
    bot_work_hours_start: int = 9
    bot_work_hours_end: int = 18
    bot_max_reminders: int = 30
    max_subscriptions_per_user: int = 5

    # ============================================
    # CELERY SETTINGS
    # ============================================
    celery_broker_url: Optional[str] = None  # Будет использоваться redis_url если не задан
    
    # ============================================
    # SECURITY
    # ============================================
    webhook_secret_key: str = "change_me_in_production"

    def model_post_init(self, __context):
        """Валидация после инициализации модели"""
        # Проверяем обязательные поля
        if not self.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set!")
        
        if not self.bitrix_webhook_url:
            logger.warning("BITRIX_WEBHOOK_URL is not set - Bitrix integration will not work")
        
        # Нормализуем database_url
        if self.database_url.startswith("postgresql://"):
            # Для asyncpg нужно заменить префикс
            self.database_url = self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        logger.info(f"Settings initialized: env={self.app_env}, timezone={self.timezone}")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_settings(self) -> dict:
        """Настройки для подключения к БД"""
        return {
            "url": self.database_url,
            "echo": self.log_level == "DEBUG",
        }

    def validate_required(self) -> bool:
        """
        Проверяет наличие всех обязательных настроек.
        
        Returns:
            True если все обязательные настройки присутствуют
        """
        errors = []
        
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        if not self.database_url:
            errors.append("DATABASE_URL is required")
        
        if errors:
            for error in errors:
                logger.error(error)
            return False
        
        return True


# Глобальный экземпляр настроек
settings = Settings()

# Валидируем настройки после создания
if not settings.validate_required():
    logger.error("Critical settings validation failed!")
