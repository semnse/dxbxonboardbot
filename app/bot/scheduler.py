"""
Планировщик задач (APScheduler)
Ежедневная рассылка напоминаний в 9:00 МСК

Исправлено:
- Правильная инициализация APScheduler с timezone
- Корректный polling Bitrix24 с пагинацией
- Интеграция с ChatBindingRepository для отправки в чаты
- Обработка ошибок и логирование
- HTML-экранирование данных из внешних источников
"""
import asyncio
import logging
from html import escape
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from app.config import settings
from app.database.connection import get_db_session
from app.database.repository import (
    DealStateRepository,
    ClientRepository,
    ChatBindingRepository,
)
from app.database.models import Client, DealState, ChatBinding
from sqlalchemy import select
from app.services.notification_service import NotificationService
from app.services.bitrix_polling_service import BitrixPollingService
from app.services.wait_reasons_service import WaitReasonsService
from app.services.bitrix_stage_service import BitrixStageService
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

# Глобальный планировщик
_scheduler: Optional[AsyncIOScheduler] = None


def _on_job_event(event):
    """Обработчик событий планировщика"""
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.debug(f"Job {event.job_id} executed successfully")


async def start_scheduler():
    """
    Запускает планировщик задач.

    Задачи:
    - send_daily_reminders: Каждый день в 9:00 МСК (опрос Bitrix + отправка)
    - sync_with_bitrix: Синхронизация БД с Bitrix24 (каждую ночь в 3:00)
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already started")
        return

    _scheduler = AsyncIOScheduler(
        timezone=settings.timezone,
        job_defaults={
            'coalesce': True,  # Объединять пропущенные запуски
            'max_instances': 1,  # Только один экземпляр задачи одновременно
            'misfire_grace_time': 3600,  # Grace time 1 час
        }
    )

    # Подписываемся на события
    _scheduler.add_listener(_on_job_event, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)

    # Задача: Ежедневная рассылка в 9:00 МСК
    _scheduler.add_job(
        send_daily_reminders,
        trigger=CronTrigger(
            hour=settings.bot_send_time_hour,
            minute=0,
            timezone=settings.timezone,
        ),
        id="send_daily_reminders",
        name="Send daily reminders to waiting clients",
        replace_existing=True,
        max_instances=1,
    )
    logger.info(
        f"Scheduled send_daily_reminders at {settings.bot_send_time_hour}:00 {settings.timezone}"
    )

    # Задача: Синхронизация с Bitrix (каждую ночь в 3:00)
    _scheduler.add_job(
        sync_with_bitrix,
        trigger=CronTrigger(
            hour=3,
            minute=0,
            timezone=settings.timezone,
        ),
        id="sync_with_bitrix",
        name="Sync active deals with Bitrix24",
        replace_existing=True,
        max_instances=1,
    )
    logger.info("Scheduled sync_with_bitrix at 03:00")

    _scheduler.start()
    logger.info(f"Scheduler started with timezone={settings.timezone}")


async def shutdown_scheduler():
    """Останавливает планировщик"""
    global _scheduler

    if _scheduler:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
        _scheduler = None


async def send_daily_reminders():
    """
    Отправляет напоминания всем активным клиентам.

    Логика:
    1. Получаем все активные привязки чатов из БД
    2. Для каждой привязки опрашиваем Bitrix24
    3. Формируем персонализированное сообщение
    4. Отправляем в Telegram чат
    5. Логируем отправку
    """
    logger.info("=" * 60)
    logger.info("Starting daily reminder job")
    logger.info("=" * 60)

    start_time = datetime.now()
    sent_count = 0
    error_count = 0
    skipped_count = 0

    try:
        # Получаем все активные привязки чатов из БД
        async with get_db_session() as session:
            chat_binding_repo = ChatBindingRepository(session)
            result = await session.execute(
                select(ChatBinding).where(ChatBinding.is_active == True)
            )
            active_bindings = result.scalars().all()

        logger.info(f"Found {len(active_bindings)} active chat bindings")

        bitrix_polling = BitrixPollingService()
        telegram_service = TelegramService()

        for binding in active_bindings:
            try:
                chat_id = binding.chat_id
                message_thread_id = binding.message_thread_id

                # Получаем данные из Bitrix
                full_item = await bitrix_polling.get_item_by_id(int(binding.bitrix_deal_id))

                if not full_item:
                    logger.warning(f"Item {binding.bitrix_deal_id} not found in Bitrix, skipping")
                    skipped_count += 1
                    continue

                # Проверяем, на стадии ли ожидания
                stage_id = full_item.get('stageId', '')
                if not BitrixStageService.is_wait_stage(stage_id):
                    logger.debug(f"Item {binding.bitrix_deal_id} not on wait stage ({stage_id}), skipping")
                    skipped_count += 1
                    continue

                # Формируем сообщение
                message_text = _build_reminder_message(full_item, binding.company_name)

                # Отправляем в Telegram с поддержкой Topics
                result = await telegram_service.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="HTML",
                    message_thread_id=message_thread_id,
                )

                if result.ok:
                    sent_count += 1
                    logger.info(
                        f"Reminder sent to chat {chat_id} "
                        f"({binding.company_name}), msg_id={result.message_id}"
                    )
                else:
                    error_count += 1
                    logger.warning(
                        f"Failed to send to chat {chat_id}: {result.description}"
                    )

            except Exception as e:
                error_count += 1
                logger.exception(f"Error processing binding {binding.bitrix_deal_id}: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(
            f"Daily reminder job completed: "
            f"sent={sent_count}, errors={error_count}, skipped={skipped_count}, "
            f"elapsed={elapsed:.2f}s"
        )
        logger.info("=" * 60)

    except Exception as e:
        logger.exception(f"Fatal error in send_daily_reminders: {e}")
        raise


def _build_reminder_message(item: Dict[str, Any], company_name: str) -> str:
    """
    Формирует персонализированное сообщение на основе данных Bitrix.
    """
    inn = escape(item.get('ufCrm20_1738855110463', 'N/A'))
    stage_id = item.get('stageId', 'unknown')
    stage_name = escape(BitrixStageService.get_stage_name(stage_id))

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
    products = [escape(product_map.get(str(p), f"Продукт #{p}")) for p in raw_products]

    # Формируем action items через сервис
    action_items = WaitReasonsService.format_action_items(raw_wait_reasons)
    general_risk = escape(WaitReasonsService.get_general_risk(raw_wait_reasons, raw_products))

    # Собираем сообщение
    product_lines = [f"• {p}" for p in products]
    action_lines = [f"• {escape(action)}" for action, _ in action_items]

    text = f"""🔍 <b>{escape(company_name)}</b>, напоминаем о шагах для завершения внедрения

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
<i>✨ Docsinbox Внедрение — ваш надёжный помощник!</i>"""

    return text


async def sync_with_bitrix():
    """
    Синхронизирует активные сделки с Bitrix24.

    Получает все элементы на стадиях ожидания и обновляет локальную БД.
    """
    logger.info("Starting Bitrix sync job")

    start_time = datetime.now()
    synced_count = 0
    error_count = 0

    try:
        bitrix_polling = BitrixPollingService()
        
        # Получаем все элементы на стадиях ожидания с полной пагинацией
        bitrix_items = await bitrix_polling.get_waiting_items(limit=1000)
        logger.info(f"Bitrix sync: found {len(bitrix_items)} items on wait stages")

        async with get_db_session() as session:
            client_repo = ClientRepository(session)
            deal_state_repo = DealStateRepository(session)
            chat_binding_repo = ChatBindingRepository(session)

            for item in bitrix_items:
                try:
                    # Получаем полный элемент с UF-полями
                    full_item = await bitrix_polling.get_item_by_id(item['id'])
                    if not full_item:
                        continue

                    # Парсим элемент
                    parsed = await bitrix_polling.parse_item(full_item)
                    if not parsed:
                        continue

                    # Ищем или создаем клиента
                    client = await client_repo.get_by_bitrix_id(str(parsed['bitrix_id']))

                    if not client:
                        # Создаем нового клиента
                        from app.database.models import Client
                        client = Client(
                            bitrix_deal_id=str(parsed['bitrix_id']),
                            company_name=parsed['company_name'],
                            telegram_chat_id=parsed.get('telegram_chat_id'),
                            is_active=True,
                        )
                        session.add(client)
                        await session.flush()
                        logger.info(f"Created new client: {parsed['company_name']}")
                    else:
                        # Обновляем существующего
                        client.telegram_chat_id = parsed.get('telegram_chat_id')
                        client.company_name = parsed['company_name']
                        client.is_active = True

                    synced_count += 1

                except Exception as e:
                    error_count += 1
                    logger.exception(f"Error syncing item {item.get('id')}: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Bitrix sync completed: {synced_count} synced, {error_count} errors, "
            f"elapsed={elapsed:.2f}s"
        )

    except Exception as e:
        logger.exception(f"Fatal error in sync_with_bitrix: {e}")
        raise


async def send_test_reminder(chat_id: int, bitrix_id: int):
    """
    Отправляет тестовое напоминание в указанный чат.
    
    Используется для отладки и тестирования.
    """
    logger.info(f"Sending test reminder to chat {chat_id} for item {bitrix_id}")
    
    try:
        bitrix_polling = BitrixPollingService()
        full_item = await bitrix_polling.get_item_by_id(bitrix_id)
        
        if not full_item:
            logger.error(f"Item {bitrix_id} not found in Bitrix")
            return False
        
        company_name = full_item.get('title', 'Тестовый клиент')
        message_text = _build_reminder_message(full_item, company_name)
        
        telegram_service = TelegramService()
        result = await telegram_service.send_message(
            chat_id=chat_id,
            text=message_text,
            parse_mode="HTML"
        )
        
        if result.ok:
            logger.info(f"Test reminder sent successfully, msg_id={result.message_id}")
            return True
        else:
            logger.error(f"Failed to send test reminder: {result.description}")
            return False
            
    except Exception as e:
        logger.exception(f"Error sending test reminder: {e}")
        return False
