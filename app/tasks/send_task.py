"""
Задача отправки ежедневных отчётов в чаты/топики Telegram

Запускается ежедневно в 09:00 MSK.
Читает данные из Bitrix, отправляет в чаты где привязаны карточки.
"""
import asyncio
import json
import random
import logging

from sqlalchemy import select
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from app.celery_app import celery_app
from app.config import settings
from app.database.connection import get_session_maker
from app.database.models import ChatBinding
from app.database.models_bot import DailyReport

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.send_task.send_daily_reports")
def send_daily_reports():
    """
    Celery задача для отправки ежедневных отчётов в чаты/топики.

    Запускается ежедневно в 09:00 MSK.
    Отправляет отчёты в чаты где привязаны карточки Bitrix.
    """
    asyncio.run(_send_daily_reports())


async def _send_daily_reports():
    """Асинхронная реализация задачи отправки отчётов."""
    from app.services.bitrix_polling_service import BitrixPollingService

    bot = Bot(token=settings.telegram_bot_token)
    bitrix_service = BitrixPollingService()

    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            # Получаем все активные привязки чатов
            result = await session.execute(
                select(ChatBinding).where(ChatBinding.is_active == True)
            )
            chat_bindings = result.scalars().all()

        logger.info(f"Отправка отчётов в {len(chat_bindings)} чатов")

        if not chat_bindings:
            logger.info("Нет активных привязок чатов для отправки")
            return

        for binding in chat_bindings:
            try:
                # Получаем данные из Bitrix
                item = await bitrix_service.get_item_by_id(int(binding.bitrix_deal_id))

                if not item:
                    logger.warning(f"Не удалось получить карточку {binding.bitrix_deal_id}")
                    continue

                # Формируем отчёт
                company_name = item.get('title', binding.company_name)
                stage_id = item.get('stageId', 'unknown')
                
                lines = [f"📊 *Ежедневный отчёт: {company_name}*\n"]
                lines.append(f"📋 Стадия: `{stage_id}`")
                
                # Продукты
                products = item.get('ufCrm20_1739184606910', [])
                if products:
                    product_map = {
                        '8426': 'ЕГАИС',
                        '8428': 'Накладные',
                        '8430': 'ЮЗЭДО',
                        '8432': 'Меркурий',
                        '8434': 'Маркировка',
                    }
                    product_names = [product_map.get(str(p), f'Продукт #{p}') for p in products]
                    lines.append(f"\n✅ Продукты: {', '.join(product_names)}")
                
                # Причины ожидания
                wait_reasons = item.get('ufCrm20_1763475932592', [])
                if wait_reasons:
                    lines.append(f"\n⏳ Ожидание: {len(wait_reasons)} причин")

                message_text = "\n\n".join(lines)

                # Отправляем сообщение в чат/топик
                try:
                    # Если есть message_thread_id - отправляем в топик
                    if binding.message_thread_id:
                        await bot.send_message(
                            chat_id=binding.chat_id,
                            text=message_text,
                            parse_mode="Markdown",
                            message_thread_id=binding.message_thread_id,  # Отправка в топик!
                            disable_notification=False,
                        )
                        logger.info(
                            f"✅ Отчёт отправлен в топик {binding.message_thread_id} "
                            f"чата {binding.chat_id} (bitrix={binding.bitrix_deal_id})"
                        )
                    else:
                        # Обычный чат без топиков
                        await bot.send_message(
                            chat_id=binding.chat_id,
                            text=message_text,
                            parse_mode="Markdown",
                            disable_notification=False,
                        )
                        logger.info(f"✅ Отчёт отправлен в чат {binding.chat_id} (bitrix={binding.bitrix_deal_id})")

                except TelegramForbiddenError:
                    logger.error(f"❌ Бот заблокирован в чате {binding.chat_id}")
                    # Помечаем привязку как неактивную
                    async with session_maker() as session:
                        binding.is_active = False
                        await session.commit()
                except TelegramRetryAfter as e:
                    logger.warning(f"⏳ Flood limit: ждём {e.retry_after} сек")
                    await asyncio.sleep(e.retry_after)
                    # Пробуем ещё раз
                    if binding.message_thread_id:
                        await bot.send_message(
                            chat_id=binding.chat_id,
                            text=message_text,
                            parse_mode="Markdown",
                            message_thread_id=binding.message_thread_id,
                        )
                    else:
                        await bot.send_message(
                            chat_id=binding.chat_id,
                            text=message_text,
                            parse_mode="Markdown",
                        )

                # Записываем в лог отчётов
                async with session_maker() as session:
                    report = DailyReport(
                        user_id=0,
                        status="success",
                        error_message=f"Chat: {binding.chat_id}, Thread: {binding.message_thread_id}",
                        items_count=1,
                    )
                    session.add(report)
                    await session.commit()

            except Exception as e:
                logger.error(
                    f"❌ Не удалось отправить отчёт в чат {binding.chat_id}: {e}",
                    exc_info=True,
                )
                async with session_maker() as session:
                    report = DailyReport(
                        user_id=0,
                        status="failed",
                        error_message=str(e),
                        items_count=0,
                    )
                    session.add(report)
                    await session.commit()

            # Задержка для защиты от Flood Wait
            delay = random.uniform(0.5, 1.0)
            await asyncio.sleep(delay)

        logger.info("✅ Отправка отчётов завершена успешно")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка при отправке отчётов: {e}", exc_info=True)
        raise

    finally:
        await bot.session.close()
