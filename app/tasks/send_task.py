"""
Задача отправки ежедневных отчётов в чаты/топики Telegram

Запускается ежедневно в 09:00 MSK.
Читает данные из Bitrix, отправляет в чаты где привязаны карточки.
"""
import asyncio
import random
from html import escape
from typing import Optional, Dict, Any, List

import structlog
from sqlalchemy import select
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError

from app.celery_app import celery_app
from app.config import settings
from app.database.connection import get_session_maker
from app.database.models import ChatBinding
from app.database.models_bot import DailyReport
from app.bot import bot as telegram_bot

logger = structlog.get_logger(__name__)

# Константы для rate limiting
TELEGRAM_SEND_DELAY_MIN = 0.5  # сек между сообщениями
TELEGRAM_SEND_DELAY_MAX = 1.5  # сек (рандомизация)
MAX_RETRY_ATTEMPTS = 3  # попытки при flood limit
BITRIX_DELAY = 0.5  # сек между Bitrix API calls


async def _build_report_message(item: dict, binding: ChatBinding) -> str:
    """
    Формирует полный отчёт для отправки в чат.
    HTML-формат (единый с командой /report).

    Args:
        item: Данные из Bitrix24
        binding: Привязка чата из БД

    Returns:
        Текст сообщения в HTML
    """
    from app.services.product_actions_service import ProductActionsService
    from app.services.bitrix_stage_service import BitrixStageService
    from app.services.wait_reasons_service import WaitReasonsService

    company_name = escape(item.get("title", binding.company_name))
    stage_id = item.get("stageId", "unknown")
    stage_name = escape(BitrixStageService.get_stage_name(stage_id))
    inn = escape(item.get("ufCrm20_1738855110463", "N/A"))

    # Продукты
    raw_products = item.get("ufCrm20_1739184606910", [])
    product_codes = [str(p) for p in raw_products] if raw_products else []

    # Причины ожидания
    raw_wait_reasons = item.get("ufCrm20_1763475932592", [])

    # Форматируем продукты
    product_map = {
        "8426": "ЕГАИС",
        "8428": "Накладные",
        "8430": "ЮЗЭДО",
        "8432": "Меркурий",
        "8434": "Маркировка",
    }
    products = [escape(product_map.get(str(p), f"Продукт #{p}")) for p in raw_products]

    # Формируем action items и риски через сервис
    action_items = WaitReasonsService.format_action_items(raw_wait_reasons)
    general_risk = escape(WaitReasonsService.get_general_risk(raw_wait_reasons, raw_products))

    # Доступные действия по продуктам
    actions_by_product = ProductActionsService.get_all_actions_for_stage(stage_id, product_codes)

    # Формируем списки
    product_lines = [f"• {p}" for p in products]
    action_lines = [f"• {escape(action)}" for action, _ in action_items]

    # Собираем сообщение в HTML-формате
    text = (
        f"🔍 <b>Отчёт для {company_name}</b>\n\n"
        f"📋 <b>Данные из Bitrix24:</b>\n"
        f"• ИНН: {inn}\n"
        f"• Стадия: {stage_name}\n\n"
        f"✅ <b>Подключённые продукты:</b>\n"
        f"{chr(10).join(product_lines) if product_lines else '• Не указаны'}\n\n"
        f"⏳ <b>Осталось сделать:</b>\n"
        f"{chr(10).join(action_lines) if action_lines else '• Нет активных задач'}\n\n"
        f"💡 <b>Это важно, потому что:</b>\n"
        f"{general_risk}\n\n"
    )

    # Доступно на этой стадии
    if actions_by_product:
        actions_html = _format_actions_block_html(actions_by_product)
        text += f"{actions_html}\n\n"
    else:
        text += "✅ <b>Доступно на этой стадии:</b>\n• Нет доступных действий на текущей стадии\n\n"

    text += "---\n<i>✨ Docsinbox Внедрение — ваш надёжный помощник!</i>"

    return text


def _format_actions_block_html(actions_by_product: Dict[str, List[str]]) -> str:
    """
    Форматирует блок доступных действий для Telegram отчёта (HTML режим).

    Args:
        actions_by_product: Dict {название_продукта: [список действий]}

    Returns:
        Отформатированный текст с заголовком и маркированным списком
    """
    if not actions_by_product:
        return ""

    lines = ["✅ <b>Доступно на этой стадии:</b>"]

    for product_name, actions in actions_by_product.items():
        if not actions:
            continue

        # Заголовок продукта
        lines.append(f"• <b>{escape(product_name)}:</b>")

        # Список действий
        for action in actions:
            lines.append(f"  - {escape(action)}")

    return "\n".join(lines)


async def _send_message_with_retry(
    bot: Bot,
    chat_id: int | str,
    text: str,
    message_thread_id: Optional[int] = None,
    max_retries: int = MAX_RETRY_ATTEMPTS,
) -> Dict[str, Any]:
    """
    Отправляет сообщение с retry-логикой.

    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        text: Текст сообщения
        message_thread_id: ID топика (для Topics)
        max_retries: Максимальное количество попыток

    Returns:
        Результат отправки
    """
    for attempt in range(max_retries):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                message_thread_id=message_thread_id,
                disable_web_page_preview=True
            )
            return {"ok": True}
        except TelegramForbiddenError:
            logger.warning(f"Bot forbidden for chat {chat_id}")
            return {"ok": False, "error": "forbidden"}
        except TelegramRetryAfter as e:
            retry_after = e.retry_after
            logger.warning(f"Rate limit, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
        except TelegramAPIError as e:
            logger.error(f"Telegram API error: {e}")
            if attempt == max_retries - 1:
                return {"ok": False, "error": str(e)}
            await asyncio.sleep(2 ** attempt)

    return {"ok": False, "error": "max_retries_exceeded"}


async def _send_daily_reports():
    """
    Отправляет ежедневные отчёты всем активным клиентам.
    """
    logger.info("Starting daily reports job")

    start_time = asyncio.get_event_loop().time()
    sent_count = 0
    error_count = 0
    skipped_count = 0

    # Получаем сессию БД
    session_maker = get_session_maker()

    async with session_maker() as session:
        # Получаем все активные привязки
        result = await session.execute(
            select(ChatBinding).where(ChatBinding.is_active == True)
        )
        bindings = list(result.scalars().all())

        logger.info(f"Found {len(bindings)} active bindings")

        # Инициализируем Bitrix сервис
        from app.services.bitrix_polling_service import BitrixPollingService
        bitrix_polling = BitrixPollingService()

        # Инициализируем бота
        bot_instance = telegram_bot.bot

        for binding in bindings:
            try:
                # Получаем данные из Bitrix
                bitrix_deal_id = binding.bitrix_deal_id

                # Проверяем кэш
                cache_key = f"bitrix:item:{bitrix_deal_id}"
                from app.services.cache_service import get_cached_item, cache_item
                item = await get_cached_item(bitrix_deal_id)

                if not item:
                    # Получаем из Bitrix
                    item = await bitrix_polling.get_item_by_id(int(bitrix_deal_id))
                    if not item:
                        logger.warning(f"Item {bitrix_deal_id} not found in Bitrix")
                        skipped_count += 1
                        continue

                    # Кэшируем
                    await cache_item(bitrix_deal_id, item)

                # Проверяем стадию
                stage_id = item.get("stageId", "")
                from app.services.bitrix_stage_service import BitrixStageService
                if not BitrixStageService.is_wait_stage(stage_id):
                    logger.debug(f"Item {bitrix_deal_id} not on wait stage")
                    skipped_count += 1
                    continue

                # Формируем отчёт
                report_text = await _build_report_message(item, binding)

                # Отправляем в Telegram
                result_send = await _send_message_with_retry(
                    bot_instance,
                    chat_id=binding.chat_id,
                    text=report_text,
                    message_thread_id=binding.message_thread_id
                )

                if result_send.get("ok"):
                    sent_count += 1
                    logger.info(f"Report sent to chat {binding.chat_id}")

                    # Сохраняем в БД
                    report = DailyReport(
                        chat_id=binding.chat_id,
                        message_thread_id=binding.message_thread_id,
                        bitrix_deal_id=bitrix_deal_id,
                        status="sent"
                    )
                    session.add(report)
                    await session.commit()
                else:
                    error_count += 1
                    logger.warning(f"Failed to send to chat {binding.chat_id}: {result_send.get('error')}")

                    # Сохраняем ошибку в БД
                    report = DailyReport(
                        chat_id=binding.chat_id,
                        message_thread_id=binding.message_thread_id,
                        bitrix_deal_id=bitrix_deal_id,
                        status="error",
                        error_message=result_send.get("error")
                    )
                    session.add(report)
                    await session.commit()

                # Random delay для rate limiting
                delay = random.uniform(TELEGRAM_SEND_DELAY_MIN, TELEGRAM_SEND_DELAY_MAX)
                await asyncio.sleep(delay)

            except Exception as e:
                error_count += 1
                logger.exception(f"Error processing binding {binding.bitrix_deal_id}: {e}")

                # Сохраняем ошибку в БД
                try:
                    report = DailyReport(
                        chat_id=binding.chat_id,
                        message_thread_id=binding.message_thread_id,
                        bitrix_deal_id=binding.bitrix_deal_id,
                        status="error",
                        error_message=str(e)
                    )
                    session.add(report)
                    await session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to save error to DB: {db_error}")

    elapsed = asyncio.get_event_loop().time() - start_time
    logger.info(f"Daily reports job completed: sent={sent_count}, errors={error_count}, skipped={skipped_count}, elapsed={elapsed:.2f}s")


@celery_app.task
def send_daily_reports():
    """
    Celery задача для отправки ежедневных отчётов.
    """
    logger.info("send_daily_reports task started")
    asyncio.run(_send_daily_reports())
