"""
Сервис управления сделками
Бизнес-логика активации/деактивации клиентов
"""
import logging
from dataclasses import dataclass
from typing import Optional, List

from app.database.repository import ClientRepository, DealStateRepository
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


@dataclass
class DealActivationResult:
    """Результат активации клиента"""
    
    success: bool
    client_id: Optional[int] = None
    error: Optional[str] = None
    should_send_first_message: bool = False


class DealService:
    """
    Сервис для управления сделками и состояниями клиентов.
    
    Основная логика:
    - Активация клиента при переходе в стадию ожидания
    - Деактивация при выходе из стадии
    - Валидация данных перед активацией
    """
    
    def __init__(
        self,
        client_repo: ClientRepository,
        deal_state_repo: DealStateRepository,
        notification_service: NotificationService,
    ):
        self.client_repo = client_repo
        self.deal_state_repo = deal_state_repo
        self.notification_service = notification_service
    
    async def activate_waiting_client(
        self,
        bitrix_deal_id: str,
        company_name: str,
        telegram_chat_id: Optional[int] = None,
        wait_reasons: Optional[List[str]] = None,
        product_codes: Optional[List[str]] = None,
    ) -> DealActivationResult:
        """
        Активирует бота для клиента при переходе в стадию ожидания.
        
        Args:
            bitrix_deal_id: ID сделки в Bitrix
            company_name: Название компании
            telegram_chat_id: ID чата Telegram
            wait_reasons: Список причин ожидания (коды)
            product_codes: Список кодов продуктов
        
        Returns:
            DealActivationResult с результатом операции
        """
        wait_reasons = wait_reasons or []
        product_codes = product_codes or []
        
        # ============================================
        # Валидация
        # ============================================
        validation_error = self._validate_activation_data(
            telegram_chat_id=telegram_chat_id,
            wait_reasons=wait_reasons,
            product_codes=product_codes,
        )
        
        if validation_error:
            logger.warning(
                f"Validation failed for deal {bitrix_deal_id}: {validation_error}"
            )
            return DealActivationResult(
                success=False,
                error=validation_error,
            )
        
        # ============================================
        # Поиск или создание клиента
        # ============================================
        client = await self.client_repo.get_by_bitrix_id(bitrix_deal_id)
        
        if not client:
            # Создаём нового клиента
            client = await self.client_repo.create_with_products(
                bitrix_deal_id=bitrix_deal_id,
                company_name=company_name,
                telegram_chat_id=telegram_chat_id,
                product_codes=product_codes,
            )
            logger.info(f"Created new client: {client.id} ({company_name})")
        else:
            # Обновляем существующего
            update_data = {
                "company_name": company_name,
                "telegram_chat_id": telegram_chat_id,
                "is_active": True,
            }
            await self.client_repo.update(client.id, **update_data)
            
            # Обновляем продукты
            await self._update_client_products(client.id, product_codes)
            
            logger.info(f"Updated existing client: {client.id} ({company_name})")
        
        # ============================================
        # Получаем ID стадии ожидания
        # ============================================
        # TODO: Загружать из БД, а не хардкодить
        WAIT_STAGE_ID = 1  # Заглушка, в реальности — запрос к БД
        
        # ============================================
        # Активация состояния сделки
        # ============================================
        deal_state = await self.deal_state_repo.activate_bot(
            client_id=client.id,
            stage_id=WAIT_STAGE_ID,
            wait_reasons=wait_reasons,
        )
        
        logger.info(
            f"Bot activated for client {client.id}, "
            f"reasons={wait_reasons}, stage_id={WAIT_STAGE_ID}"
        )
        
        # ============================================
        # Проверка: нужно ли отправлять первое сообщение?
        # ============================================
        # Отправляем, если:
        # - Это первая активация (messages_sent_count == 0)
        # - Telegram chat заполнен
        should_send = (
            deal_state.messages_sent_count == 0
            and client.telegram_chat_id is not None
        )
        
        return DealActivationResult(
            success=True,
            client_id=client.id,
            should_send_first_message=should_send,
        )
    
    async def deactivate_client(self, client_id: int) -> bool:
        """
        Деактивирует бота для клиента (при смене стадии).
        """
        return await self.deal_state_repo.deactivate_bot(client_id)
    
    def _validate_activation_data(
        self,
        telegram_chat_id: Optional[int],
        wait_reasons: List[str],
        product_codes: List[str],
    ) -> Optional[str]:
        """
        Валидирует данные для активации.
        
        Returns:
            Текст ошибки или None (если всё ок)
        """
        # Проверка Telegram
        if not telegram_chat_id:
            return "Не указан Telegram-чат клиента"
        
        # Проверка причин
        if not wait_reasons:
            return "Не выбраны причины ожидания"
        
        if len(wait_reasons) > 5:
            return "Слишком много причин (макс. 5)"
        
        # Проверка продуктов
        if not product_codes:
            return "К клиенту не привязано ни одного продукта"
        
        return None
    
    async def _update_client_products(
        self,
        client_id: int,
        product_codes: List[str],
    ) -> None:
        """
        Обновляет список продуктов клиента.
        TODO: Реализовать полную синхронизацию продуктов.
        """
        # В MVP просто логируем
        logger.debug(
            f"Product sync for client {client_id}: {product_codes}"
        )
