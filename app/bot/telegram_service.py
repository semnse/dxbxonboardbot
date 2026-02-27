"""
Telegram Service
Клиент для работы с Telegram Bot API

Этот модуль ре-экспортирует TelegramService из app.services.telegram_service
для обратной совместимости.
"""
# Ре-экспорт для обратной совместимости
from app.services.telegram_service import (
    TelegramService,
    TelegramResponse,
    ChatInfo,
)

__all__ = [
    "TelegramService",
    "TelegramResponse",
    "ChatInfo",
]
