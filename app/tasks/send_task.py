"""
Задача отправки ежедневных отчётов пользователям

Запускается ежедневно в 09:00 MSK.
Читает данные из Redis кэша, отправляет в Telegram.
"""
import asyncio
import json
import random
import logging

from sqlalchemy import select
from aiogram import Bot

from app.celery_app import celery_app
from app.config import settings
from app.database.connection import get_session_maker
from app.database.models_bot import User, Subscription, DailyReport

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.send_task.send_daily_reports")
def send_daily_reports():
    """
    Celery задача для отправки ежедневных отчётов пользователям.

    Запускается ежедневно в 09:00 MSK.
    Читает данные из Redis кэша, отправляет в Telegram.
    """
    asyncio.run(_send_daily_reports())


async def _send_daily_reports():
    """Асинхронная реализация задачи отправки отчётов."""
    import redis.asyncio as aioredis

    bot = Bot(token=settings.telegram_bot_token)
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    try:
        session_maker = get_session_maker()
        async with session_maker() as session:
            # Получаем всех активных пользователей
            result = await session.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()

        logger.info(f"Отправка отчётов {len(users)} активным пользователям")

        if not users:
            logger.info("Нет активных пользователей для отправки")
            return

        for user in users:
            try:
                async with session_maker() as session:
                    # Получаем подписки пользователя
                    result = await session.execute(
                        select(Subscription).where(Subscription.user_id == user.id)
                    )
                    subs = result.scalars().all()

                if not subs:
                    continue

                # Формируем отчёт
                lines = ["📊 *Ежедневный отчёт Bitrix24*\n"]
                items_count = 0

                for sub in subs:
                    cache_key = f"bitrix:item:{sub.bitrix_item_id}"
                    cached = await redis_client.get(cache_key)

                    if cached:
                        item = json.loads(cached)
                        # Для смарт-процессов используем правильные поля (lowercase)
                        title = (
                            item.get("title")
                            or item.get("TITLE")
                            or item.get("name")
                            or item.get("NAME")
                            or item.get("company_title")
                            or item.get("COMPANY_TITLE")
                            or f"ID {sub.bitrix_item_id}"
                        )
                        stage = (
                            item.get("stageId")
                            or item.get("STAGE_ID")
                            or item.get("stage")
                            or item.get("STAGE")
                            or "—"
                        )
                        lines.append(f"📌 *{title}*\nСтатус: `{stage}`")
                        items_count += 1
                    else:
                        lines.append(
                            f"⚠️ Карточка {sub.bitrix_item_id}: нет данных"
                        )

                # Отправляем сообщение
                await bot.send_message(
                    user.tg_id,
                    "\n\n".join(lines),
                    parse_mode="Markdown",
                )

                # Записываем успешную отправку в лог
                async with session_maker() as session:
                    report = DailyReport(
                        user_id=user.id,
                        status="success",
                        items_count=items_count,
                    )
                    session.add(report)
                    await session.commit()

                logger.debug(f"Отчёт отправлен пользователю {user.tg_id}")

            except Exception as e:
                logger.error(
                    f"Не удалось отправить отчёт пользователю {user.tg_id}: {e}",
                    exc_info=True,
                )
                # Записываем ошибку в лог
                async with session_maker() as session:
                    report = DailyReport(
                        user_id=user.id,
                        status="failed",
                        error_message=str(e),
                    )
                    session.add(report)
                    await session.commit()

            # Задержка для защиты от Telegram Flood Wait (0.5-1.0 сек)
            delay = random.uniform(0.5, 1.0)
            await asyncio.sleep(delay)

        logger.info("Отправка отчётов завершена успешно")

    except Exception as e:
        logger.error(f"Критическая ошибка при отправке отчётов: {e}", exc_info=True)
        raise

    finally:
        await bot.session.close()
        await redis_client.close()
