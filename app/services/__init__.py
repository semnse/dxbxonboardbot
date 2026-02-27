"""
Services module
"""
from app.services.deal_service import DealService, DealActivationResult
from app.services.notification_service import NotificationService
from app.services.bitrix_service import BitrixService
from app.services.bitrix_polling_service import BitrixPollingService
from app.services.bitrix_stage_service import BitrixStageService
from app.services.wait_reasons_service import WaitReasonsService
from app.services.telegram_service import TelegramService, TelegramResponse, ChatInfo

__all__ = [
    # Deal service
    "DealService",
    "DealActivationResult",
    # Notification service
    "NotificationService",
    # Bitrix services
    "BitrixService",
    "BitrixPollingService",
    "BitrixStageService",
    # Other services
    "WaitReasonsService",
    "TelegramService",
    "TelegramResponse",
    "ChatInfo",
]
