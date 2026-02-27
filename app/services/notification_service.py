"""
Сервис уведомлений
Отправка сообщений в Telegram, логирование

Исправлено:
- Правильная интеграция с WaitReasonsService
- Использование ChatBindingRepository для отправки в чаты
- Обработка ошибок и логирование
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.config import settings
from app.database.connection import get_db_session
from app.database.repository import (
    ClientRepository,
    ProductRepository,
    DealStateRepository,
    MessageLogRepository,
    ChatBindingRepository,
)
from app.database.models import Client, DealState, ChatBinding
from app.services.wait_reasons_service import WaitReasonsService
from app.services.bitrix_stage_service import BitrixStageService
from app.services.telegram_service import TelegramService
from app.services.bitrix_polling_service import BitrixPollingService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Сервис для отправки уведомлений клиентам.
    """

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.max_reminders = settings.bot_max_reminders
        self.work_hours_start = settings.bot_work_hours_start
        self.work_hours_end = settings.bot_work_hours_end

    async def send_reminder(self, client_id: int) -> bool:
        """
        Отправляет ежедневное напоминание клиенту.

        Использует данные из БД и сервисы для формирования персонализированного сообщения.
        """
        logger.info(f"Sending reminder to client {client_id}")

        async with get_db_session() as session:
            client_repo = ClientRepository(session)
            deal_state_repo = DealStateRepository(session)

            # Получаем клиента
            client = await client_repo.get_by_bitrix_id(str(client_id))
            if not client:
                logger.warning(f"Client {client_id} not found")
                return False

            if not client.telegram_chat_id:
                logger.warning(f"Client {client_id} has no Telegram chat ID")
                return False

            # Получаем состояние сделки
            deal_state = await deal_state_repo.get_by_client_id(client.id)
            if not deal_state or not deal_state.is_bot_active:
                logger.debug(f"Client {client_id} bot is not active")
                return False

            # Формируем сообщение
            message_text = await self._build_reminder_message(client, deal_state)

            # Отправляем в Telegram
            telegram_service = TelegramService()
            result = await telegram_service.send_message(
                chat_id=client.telegram_chat_id,
                text=message_text,
                parse_mode="HTML"
            )

            if result.ok:
                logger.info(f"Reminder sent to client {client_id} (msg_id={result.message_id})")
                
                # Логируем отправку
                try:
                    message_log_repo = MessageLogRepository(session)
                    await message_log_repo.log_sent(
                        client_id=client.id,
                        message_type="reminder",
                        message_text=message_text[:500],  # Обрезаем для лога
                        telegram_message_id=result.message_id,
                    )
                except Exception as e:
                    logger.error(f"Failed to log message: {e}")
                
                return True
            else:
                logger.error(f"Failed to send reminder to client {client_id}: {result.description}")
                
                # Логируем ошибку
                try:
                    message_log_repo = MessageLogRepository(session)
                    await message_log_repo.log_failed(
                        client_id=client.id,
                        message_type="reminder",
                        message_text=message_text[:500],
                        error_message=result.description,
                    )
                except Exception as e:
                    logger.error(f"Failed to log error: {e}")
                
                return False

    async def send_reminder_to_chat(self, chat_binding: ChatBinding) -> bool:
        """
        Отправляет напоминание в чат на основе привязки.
        
        Args:
            chat_binding: Привязка чата к Bitrix карточке
            
        Returns:
            True если сообщение отправлено успешно
        """
        logger.info(f"Sending reminder to chat {chat_binding.chat_id} for {chat_binding.company_name}")
        
        try:
            # Получаем данные из Bitrix
            bitrix_polling = BitrixPollingService()
            full_item = await bitrix_polling.get_item_by_id(int(chat_binding.bitrix_deal_id))
            
            if not full_item:
                logger.warning(f"Item {chat_binding.bitrix_deal_id} not found in Bitrix")
                return False
            
            # Проверяем стадию
            stage_id = full_item.get('stageId', '')
            if not BitrixStageService.is_wait_stage(stage_id):
                logger.debug(f"Item {chat_binding.bitrix_deal_id} not on wait stage")
                return False
            
            # Формируем сообщение
            message_text = self._build_message_from_bitrix(full_item, chat_binding.company_name)
            
            # Отправляем в Telegram
            telegram_service = TelegramService()
            result = await telegram_service.send_message(
                chat_id=chat_binding.chat_id,
                text=message_text,
                parse_mode="HTML"
            )
            
            if result.ok:
                logger.info(f"Reminder sent to chat {chat_binding.chat_id} (msg_id={result.message_id})")
                return True
            else:
                logger.error(f"Failed to send to chat {chat_binding.chat_id}: {result.description}")
                return False
                
        except Exception as e:
            logger.exception(f"Error sending reminder to chat {chat_binding.chat_id}: {e}")
            return False

    async def _build_reminder_message(
        self,
        client: Client,
        deal_state: DealState
    ) -> str:
        """
        Формирует персонализированное сообщение на основе данных клиента.
        Использует WaitReasonsService для форматирования.

        Структура:
        🔍 [Название], напоминаем о шагах...

        ✅ УЖЕ ДОСТУПНО:
        • [Продукты]

        ⏳ ОСТАЛОСЬ СДЕЛАТЬ:
        • [Действие 1]
        • [Действие 2]

        💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:
        [Риск]
        """
        # Получаем данные
        company_name = client.company_name or "Клиент"

        # Получаем причины ожидания из deal_state
        wait_reasons = deal_state.wait_reasons or [] if deal_state else []

        # Получаем продукты клиента
        product_codes = [p.product_code for p in client.products] if client.products else []

        # Формируем action items через сервис WaitReasonsService
        action_items = WaitReasonsService.format_action_items(wait_reasons)
        general_risk = WaitReasonsService.get_general_risk(wait_reasons, product_codes)

        # Формируем список продуктов
        product_names = self._format_products(product_codes)
        product_lines = [f"• {p}" for p in product_names]

        # Формируем список действий
        action_lines = [f"• {action}" for action, _ in action_items]

        # Собираем сообщение
        message_parts = [
            f"🔍 <b>{company_name}</b>, напоминаем о шагах для завершения внедрения",
            "",
            "✅ УЖЕ ДОСТУПНО:",
        ]

        if product_lines:
            message_parts.extend(product_lines)
        else:
            message_parts.append("• Продукты не указаны")

        message_parts.append("")
        message_parts.append("⏳ ОСТАЛОСЬ СДЕЛАТЬ:")

        if action_lines:
            message_parts.extend(action_lines)
        else:
            message_parts.append("• Нет активных задач")

        message_parts.append("")
        message_parts.append("💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:")
        message_parts.append(general_risk)
        message_parts.append("")
        message_parts.append("<i>Бот онбординга Bitrix24</i>")

        return "\n".join(message_parts)

    def _build_message_from_bitrix(
        self,
        item: Dict[str, Any],
        company_name: str
    ) -> str:
        """
        Формирует сообщение напрямую из данных Bitrix.
        Используется для отправки в чаты через ChatBinding.
        """
        inn = item.get('ufCrm20_1738855110463', 'N/A')
        stage_id = item.get('stageId', 'unknown')
        stage_name = BitrixStageService.get_stage_name(stage_id)

        raw_products = item.get('ufCrm20_1739184606910', [])
        raw_wait_reasons = item.get('ufCrm20_1763475932592', [])

        # Форматируем продукты
        product_map = {
            '8426': 'ЕГАИС',
            '8428': 'Накладные',
            '8430': 'ЮЗЭДО',
            '8432': 'Меркурий',
            '8434': 'Маркировка',
        }
        products = [product_map.get(str(p), f"Продукт #{p}") for p in raw_products]

        # Формируем action items через сервис WaitReasonsService
        action_items = WaitReasonsService.format_action_items(raw_wait_reasons)
        general_risk = WaitReasonsService.get_general_risk(raw_wait_reasons, [])

        # Собираем сообщение
        product_lines = [f"• {p}" for p in products]
        action_lines = [f"• {action}" for action, _ in action_items]

        text = f"""🔍 <b>{company_name}</b>, напоминаем о шагах для завершения внедрения

📋 <b>Данные из Bitrix24:</b>
• ИНН: {inn}
• Стадия: {stage_name}

✅ <b>Подключённые продукты:</b>
{chr(10).join(product_lines) if product_lines else '• Не указаны'}

⏳ <b>Осталось сделать:</b>
{chr(10).join(action_lines) if action_lines else '• Нет активных задач'}

💡 <b>Это важно, потому что:</b>
{general_risk}

---
<i>Бот онбординга Bitrix24</i>"""

        return text

    def _format_products(self, product_codes: List[str]) -> List[str]:
        """Форматирует коды продуктов в названия"""
        product_map = {
            'ЕГАИС': 'ЕГАИС',
            'NAKLADNIE': 'Накладные',
            'YZEDO': 'ЮЗЭДО',
            'MERCURY': 'Меркурий',
            'MARKING': 'Маркировка',
            # Числовые коды из Bitrix
            '8426': 'ЕГАИС',
            '8428': 'Накладные',
            '8430': 'ЮЗЭДО',
            '8432': 'Меркурий',
            '8434': 'Маркировка',
        }

        result = []
        for code in product_codes:
            name = product_map.get(str(code))
            if name:
                result.append(name)
            else:
                result.append(f"Продукт #{code}")

        return result

    async def send_first_message(self, client_id: int) -> bool:
        """Отправляет первое сообщение при активации"""
        logger.info(f"Sending first message to client {client_id}")

        async with get_db_session() as session:
            client_repo = ClientRepository(session)
            client = await client_repo.get_by_bitrix_id(str(client_id))

            if not client or not client.telegram_chat_id:
                return False

            # Проверяем, рабочее ли время
            if not self._is_work_hours():
                logger.info(f"Not work hours, skipping first message for client {client_id}")
                return True

            message = f"""
👋 Здравствуйте, {client.company_name}!

Мы запустили бота напоминаний, чтобы помочь вам быстрее завершить внедрение.

Бот будет напоминать о шагах, которые нужно сделать, и объяснять,
почему это важно для вашего бизнеса.

Если у вас возникнут вопросы — просто напишите вашему менеджеру внедрения.
"""

            telegram = TelegramService()
            result = await telegram.send_message(client.telegram_chat_id, message)

            return result.ok

    async def send_stop_message(self, client_id: int) -> bool:
        """Отправляет сообщение при деактивации бота"""
        logger.info(f"Sending stop message to client {client_id}")

        async with get_db_session() as session:
            client_repo = ClientRepository(session)
            client = await client_repo.get_by_bitrix_id(str(client_id))

            if not client or not client.telegram_chat_id:
                return False

            message = f"""
✅ {client.company_name}, отличные новости!

Ваша сделка перешла на следующий этап. Бот напоминаний больше не будет
отправлять сообщения по этой сделке.

Если вам понадобится помощь — обращайтесь к вашему менеджеру внедрения.
"""

            telegram = TelegramService()
            result = await telegram.send_message(client.telegram_chat_id, message)

            return result.ok

    def _is_work_hours(self) -> bool:
        """Проверяет, рабочее ли время (9:00-18:00 МСК)"""
        from app.utils.timezone import get_msk_time
        now = get_msk_time()
        return self.work_hours_start <= now.hour < self.work_hours_end
