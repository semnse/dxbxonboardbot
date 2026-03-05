"""
Задача отправки ежедневных отчётов в чаты/топики Telegram

Запускается ежедневно в 09:00 MSK.
Читает данные из Bitrix, отправляет в чаты где привязаны карточки.
"""
import asyncio
import random
from typing import Optional, Dict, Any

import structlog
from sqlalchemy import select
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError

from app.celery_app import celery_app
from app.config import settings
from app.database.connection import get_session_maker
from app.database.models import ChatBinding
from app.database.models_bot import DailyReport

logger = structlog.get_logger(__name__)

# Константы для rate limiting
TELEGRAM_SEND_DELAY_MIN = 0.5  # сек между сообщениями
TELEGRAM_SEND_DELAY_MAX = 1.5  # сек (рандомизация)
MAX_RETRY_ATTEMPTS = 3  # попытки при flood limit
BITRIX_DELAY = 0.5  # сек между Bitrix API calls


@celery_app.task(
    name="app.tasks.send_task.send_daily_reports",
    time_limit=1800,  # 30 минут максимум
    soft_time_limit=1500,  # 25 минут мягкий лимит
    acks_late=True,  # Подтверждение после выполнения
)
def send_daily_reports():
    """
    Celery задача для отправки ежедневных отчётов в чаты/топики.

    Запускается ежедневно в 09:00 MSK.
    Отправляет отчёты в чаты где привязаны карточки Bitrix.
    """
    asyncio.run(_send_daily_reports())


def _build_report_message(item: dict, binding: ChatBinding) -> str:
    """
    Формирует текст отчёта из данных Bitrix.

    Args:
        item: Данные карточки из Bitrix
        binding: Привязка чата

    Returns:
        Текст сообщения в Markdown
    """
    company_name = item.get("title", binding.company_name)
    stage_id = item.get("stageId", "unknown")

    lines = [f"📊 *Ежедневный отчёт: {company_name}*\n"]
    lines.append(f"📋 Стадия: `{stage_id}`")

    # Продукты
    products = item.get("ufCrm20_1739184606910", [])
    if products:
        product_map = {
            "8426": "ЕГАИС",
            "8428": "Накладные",
            "8430": "ЮЗЭДО",
            "8432": "Меркурий",
            "8434": "Маркировка",
        }
        product_names = [product_map.get(str(p), f"Продукт #{p}") for p in products]
        lines.append(f"\n✅ Продукты: {', '.join(product_names)}")

    # Причины ожидания
    wait_reasons = item.get("ufCrm20_1763475932592", [])
    if wait_reasons:
        lines.append(f"\n⏳ Ожидание: {len(wait_reasons)} причин")

    return "\n\n".join(lines)


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
        Dict со статусом отправки
    """
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Отправка в топик или обычный чат
            if message_thread_id and message_thread_id > 0:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                    message_thread_id=message_thread_id,
                    disable_notification=False,
                )
                logger.info(
                    "report_sent_to_topic",
                    chat_id=chat_id,
                    thread_id=message_thread_id,
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                    disable_notification=False,
                )
                logger.info("report_sent_to_chat", chat_id=chat_id)

            return {"success": True, "retry_count": retry_count}

        except TelegramForbiddenError:
            logger.error("bot_blocked_in_chat", chat_id=chat_id)
            return {"success": False, "blocked": True, "retry_count": retry_count}

        except TelegramRetryAfter as e:
            retry_count += 1
            retry_delay = min(e.retry_after, 300)  # Cap на 5 минут

            if retry_count >= max_retries:
                logger.error(
                    "max_retries_exceeded",
                    chat_id=chat_id,
                    retry_count=retry_count,
                )
                return {"success": False, "retry_count": retry_count}

            logger.warning(
                "flood_limit_hit",
                retry_after=retry_delay,
                attempt=retry_count,
                chat_id=chat_id,
            )
            await asyncio.sleep(retry_delay)

        except TelegramAPIError as e:
            logger.error("telegram_send_error", chat_id=chat_id, error=str(e))
            return {"success": False, "retry_count": retry_count}

    return {"success": False, "retry_count": retry_count}


async def _log_report(
    session_maker,
    binding: ChatBinding,
    status: str,
    error_message: Optional[str] = None,
):
    """Записывает отчёт в БД"""
    async with session_maker() as session:
        report = DailyReport(
            user_id=0,  # TODO: создать системного пользователя
            status=status,
            error_message=error_message or f"Chat: {binding.chat_id}, Thread: {binding.message_thread_id}",
            items_count=1 if status == "success" else 0,
        )
        session.add(report)
        await session.commit()


async def _deactivate_binding(session_maker, binding: ChatBinding):
    """Деактивирует привязку при блокировке"""
    async with session_maker() as session:
        binding.is_active = False
        await session.commit()


async def _get_bitrix_item_with_retry(
    bitrix_service,
    bitrix_deal_id: str,
    max_retries: int = 3,
):
    """Получает данные из Bitrix с retry-логикой"""
    from app.services.bitrix_polling_service import BitrixPollingService

    for attempt in range(max_retries):
        try:
            item = await asyncio.wait_for(
                bitrix_service.get_item_by_id(int(bitrix_deal_id)),
                timeout=15.0,
            )
            return item
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                delay = 2.0 * (2**attempt)  # Exponential backoff
                logger.warning(
                    "bitrix_timeout_retry",
                    bitrix_deal_id=bitrix_deal_id,
                    delay=delay,
                    attempt=attempt + 1,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "bitrix_timeout_exceeded",
                    bitrix_deal_id=bitrix_deal_id,
                    max_retries=max_retries,
                )
                return None
        except Exception as e:
            logger.error(
                "bitrix_request_error",
                bitrix_deal_id=bitrix_deal_id,
                error=str(e),
            )
            return None

    return None


async def _send_daily_reports():
    """Асинхронная реализация задачи отправки отчётов."""
    from app.services.bitrix_polling_service import BitrixPollingService

    bot = None
    bitrix_service = BitrixPollingService()

    # Статистика
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "blocked": 0,
        "skipped": 0,
        "bitrix_retry": 0,
        "telegram_retry": 0,
    }

    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            # Получаем все активные привязки чатов
            result = await session.execute(
                select(ChatBinding).where(ChatBinding.is_active == True)
            )
            chat_bindings = result.scalars().all()

        stats["total"] = len(chat_bindings)
        logger.info("starting_daily_reports", count=stats["total"])

        if not chat_bindings:
            logger.info("no_active_chat_bindings")
            return

        for idx, binding in enumerate(chat_bindings):
            # Проверка активности
            if not binding.is_active:
                logger.debug(
                    "skipping_inactive_binding",
                    chat_id=binding.chat_id,
                    bitrix_deal_id=binding.bitrix_deal_id,
                )
                stats["skipped"] += 1
                continue

            # Rate limiting - задержка перед отправкой
            if idx > 0:
                delay = random.uniform(TELEGRAM_SEND_DELAY_MIN, TELEGRAM_SEND_DELAY_MAX)
                await asyncio.sleep(delay)

            try:
                # Получаем данные из Bitrix с retry
                item = await _get_bitrix_item_with_retry(
                    bitrix_service, binding.bitrix_deal_id
                )

                if not item:
                    logger.warning(
                        "bitrix_item_not_found",
                        bitrix_deal_id=binding.bitrix_deal_id,
                    )
                    stats["failed"] += 1
                    await _log_report(
                        session_maker,
                        binding,
                        "failed",
                        f"Bitrix item not found: {binding.bitrix_deal_id}",
                    )
                    continue

                # Формируем отчёт
                message_text = _build_report_message(item, binding)

                # Отправляем с retry-логикой
                result = await _send_message_with_retry(
                    bot,
                    binding.chat_id,
                    message_text,
                    binding.message_thread_id,
                )

                if result["success"]:
                    stats["success"] += 1
                    if result["retry_count"] > 0:
                        stats["telegram_retry"] += result["retry_count"]
                    await _log_report(session_maker, binding, "success")
                elif result.get("blocked"):
                    stats["blocked"] += 1
                    stats["failed"] += 1
                    await _deactivate_binding(session_maker, binding)
                    await _log_report(
                        session_maker,
                        binding,
                        "failed",
                        "Bot blocked in chat",
                    )
                else:
                    stats["failed"] += 1
                    if result["retry_count"] > 0:
                        stats["telegram_retry"] += result["retry_count"]
                    await _log_report(
                        session_maker,
                        binding,
                        "failed",
                        "Send failed after retries",
                    )

            except Exception as e:
                logger.error(
                    "unexpected_error_sending_report",
                    chat_id=binding.chat_id,
                    bitrix_deal_id=binding.bitrix_deal_id,
                    error=str(e),
                    exc_info=True,
                )
                stats["failed"] += 1
                await _log_report(
                    session_maker,
                    binding,
                    "failed",
                    str(e),
                )

        logger.info(
            "daily_reports_completed",
            total=stats["total"],
            success=stats["success"],
            failed=stats["failed"],
            blocked=stats["blocked"],
            skipped=stats["skipped"],
            bitrix_retry=stats["bitrix_retry"],
            telegram_retry=stats["telegram_retry"],
        )

    except Exception as e:
        logger.error(
            "critical_error_sending_reports",
            error=str(e),
            exc_info=True,
        )
        raise

    finally:
        if bot:
            await bot.session.close()
