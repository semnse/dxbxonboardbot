"""
Webhook endpoints для внешних сервисов (Bitrix24, Telegram)

Поддерживает:
- Смарт-процессы Bitrix24 (Dynamic Type 1070)
- Обычные сделки CRM
"""
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.database.repository import (
    ClientRepository,
    DealStateRepository,
    MessageLogRepository,
)
from app.services.deal_service import DealService
from app.services.notification_service import NotificationService
from app.services.bitrix_smart_api import BitrixSmartProcessAPI
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Bitrix24 Webhook Payloads
# ============================================
class BitrixSmartProcessPayload(BaseModel):
    """Модель данных от Bitrix24 при обновлении смарт-процесса"""
    
    event: str = Field(..., description="Тип события")
    data: dict = Field(..., description="Данные элемента")
    timestamp: Optional[str] = Field(None, description="Время события")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event": "ONCRMDYNAMICITEMUPDATE",
                "data": {
                    "ID": "123",
                    "ENTITY_TYPE_ID": "1070",
                    "STAGE_ID": "3150",
                    "CATEGORY_ID": "38",
                    "TITLE": "ООО Восток"
                },
                "timestamp": "2026-02-26T10:30:00Z"
            }
        }


class BitrixWebhookResponse(BaseModel):
    """Ответ на webhook от Bitrix24"""
    status: str
    message: str
    item_id: Optional[str] = None


# ============================================
# Bitrix Smart Process Webhook Handler
# ============================================
@router.post("/bitrix/smart", response_model=BitrixWebhookResponse)
async def bitrix_smart_webhook(
    payload: BitrixSmartProcessPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_bitrix_signature: Optional[str] = Header(None, alias="X-Bitrix-Signature"),
):
    """
    Обработчик webhook от Bitrix24 при обновлении смарт-процесса.
    
    События:
    - ONCRMDYNAMICITEMUPDATE: Обновление элемента смарт-процесса
    
    Логика:
    1. Проверяем стадию элемента
    2. Если "ЖДЁМ_ДЕЙСТВИЙ_КЛИЕНТА" (3150) → активируем бота
    3. Если другая стадия → деактивируем бота
    4. Отправляем первое сообщение (если активация)
    """
    logger.info(
        f"Received Bitrix smart process webhook: "
        f"event={payload.event}, item_id={payload.data.get('ID')}"
    )
    
    # Валидация типа сущности
    entity_type_id = payload.data.get('ENTITY_TYPE_ID')
    if entity_type_id != '1070':
        logger.warning(f"Wrong entity type: {entity_type_id}")
        return BitrixWebhookResponse(
            status="ignored",
            message=f"Wrong entity type: {entity_type_id}",
        )
    
    item_data = payload.data
    item_id = item_data.get('ID')
    stage_id = item_data.get('STAGE_ID')
    
    if not item_id:
        raise HTTPException(status_code=400, detail="Item ID is required")
    
    # Инициализация API
    bitrix_api = BitrixSmartProcessAPI(
        webhook_url=settings.bitrix_webhook_url,
        entity_type_id=1070,
        category_id=38,
        target_stage_id="3150",
    )
    
    # Проверка: стадия ожидания?
    WAIT_STAGE_ID = "3150"
    is_wait_stage = str(stage_id) == WAIT_STAGE_ID
    
    try:
        if is_wait_stage:
            # Получаем полные данные элемента
            full_item = await bitrix_api.get_item(int(item_id))
            
            if not full_item:
                return BitrixWebhookResponse(
                    status="error",
                    message=f"Item {item_id} not found",
                )
            
            # Извлекаем данные
            telegram_chat = bitrix_api.extract_telegram_chat_id(full_item)
            wait_reasons = bitrix_api.extract_wait_reasons(full_item)
            products = bitrix_api.extract_product_codes(full_item)
            company_name = bitrix_api.extract_company_name(full_item)
            
            # Валидация
            if not telegram_chat:
                return BitrixWebhookResponse(
                    status="warning",
                    message="No Telegram chat ID",
                    item_id=item_id,
                )
            
            if not wait_reasons:
                return BitrixWebhookResponse(
                    status="warning",
                    message="No wait reasons",
                    item_id=item_id,
                )
            
            # TODO: Сохранить в БД и активировать бота
            # В MVP просто логируем
            logger.info(
                f"Bot activation for item {item_id}: "
                f"company={company_name}, "
                f"telegram={telegram_chat}, "
                f"reasons={wait_reasons}, "
                f"products={products}"
            )
            
            # TODO: Отправить первое сообщение
            # background_tasks.add_task(
            #     notification_service.send_first_message,
            #     item_id=item_id,
            # )
            
            return BitrixWebhookResponse(
                status="success",
                message="Bot activated for smart process item",
                item_id=item_id,
            )
        else:
            # Деактивация бота
            logger.info(f"Bot deactivated for item {item_id} (stage={stage_id})")
            
            return BitrixWebhookResponse(
                status="success",
                message="Bot deactivated (stage changed)",
                item_id=item_id,
            )
    
    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        # Не возвращаем ошибку Bitrix, чтобы не триггерить retry
        return BitrixWebhookResponse(
            status="error",
            message=f"Internal error: {str(e)}",
            item_id=item_id,
        )


# ============================================
# Bitrix Deal Webhook Handler (для совместимости)
# ============================================
@router.post("/bitrix/deal", response_model=BitrixWebhookResponse)
async def bitrix_deal_webhook(
    payload: BitrixSmartProcessPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Обработчик webhook от Bitrix24 для обычных сделок.
    (Для совместимости, если используется CRM продажников)
    """
    logger.warning(
        "Deal webhook called, but smart process is preferred. "
        "Use /webhook/bitrix/smart instead."
    )
    
    return BitrixWebhookResponse(
        status="ignored",
        message="Use /webhook/bitrix/smart for smart processes",
    )


# ============================================
# Test Endpoint
# ============================================
@router.post("/bitrix/test")
async def bitrix_test_webhook():
    """
    Тестовый endpoint для проверки webhook.
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint is working",
        "timestamp": datetime.utcnow().isoformat(),
    }
