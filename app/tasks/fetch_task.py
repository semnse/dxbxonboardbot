"""
Задача сбора статусов из Bitrix24

Запускается ежедневно в 08:00 MSK.
Сохраняет данные в Redis кэш на 24 часа.
"""
import asyncio
import json
import time
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.config import settings
from app.database.connection import get_session_maker
from app.database.models_bot import Subscription

logger = logging.getLogger(__name__)

# Задержка между запросами для соблюдения лимита Bitrix API (2 запроса/сек)
BITRIX_RATE_LIMIT_DELAY = 0.5


@celery_app.task(name="app.tasks.fetch_task.fetch_daily_statuses")
def fetch_daily_statuses():
    """
    Celery задача для сбора статусов карточек из Bitrix24.

    Запускается ежедневно в 08:00 MSK.
    Сохраняет данные в Redis кэш на 24 часа.
    """
    asyncio.run(_fetch_daily_statuses())


async def _fetch_daily_statuses():
    """Асинхронная реализация задачи сбора статусов."""
    from app.services.bitrix_polling_service import BitrixPollingService
    import redis.asyncio as aioredis

    bitrix_service = BitrixPollingService()
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    try:
        # Получаем все подписки из БД
        session_maker = get_session_maker()
        async with session_maker() as session:
            result = await session.execute(select(Subscription))
            subs = result.scalars().all()

        logger.info(f"Начало сбора статусов для {len(subs)} подписок")

        if not subs:
            logger.info("Нет активных подписок для сбора")
            return

        # Получаем данные из смарт-процесса Bitrix24 (ВСЕ карточки!)
        deals = await bitrix_service.get_waiting_items(limit=2000)
        logger.info(f"Получено {len(deals)} сделок из Bitrix24")

        # Создаём мап ID -> сделка для быстрого поиска (используем lowercase 'id')
        deals_map = {str(deal.get('id')): deal for deal in deals}

        # Последовательно обрабатываем подписки с rate limiting
        for sub in subs:
            # Ищем сделку в мапе
            item = deals_map.get(sub.bitrix_item_id)

            if item:
                # Сохраняем в Redis кэш на 24 часа
                cache_key = f"bitrix:item:{sub.bitrix_item_id}"
                await redis_client.set(
                    cache_key,
                    json.dumps(item, ensure_ascii=False),
                    ex=86400,  # 24 часа
                )
                logger.debug(f"Закэширована карточка {sub.bitrix_item_id}")
            else:
                logger.warning(f"Сделка {sub.bitrix_item_id} не найдена в Bitrix24")

            # Соблюдаем rate limit Bitrix API
            await asyncio.sleep(BITRIX_RATE_LIMIT_DELAY)

        logger.info("Сбор статусов завершён успешно")

    except Exception as e:
        logger.error(f"Ошибка при сборе статусов: {e}", exc_info=True)
        raise

    finally:
        await redis_client.close()
