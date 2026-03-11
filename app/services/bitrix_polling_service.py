"""
Bitrix24 Polling Service
Опрос смарт-процесса "Торговые точки" для получения активных клиентов

Исправлено:
- Полная пагинация для получения всех карточек (591+)
- Правильная обработка стадий ожидания
- Retry логика для transient ошибок
- Детальное логирование
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional

import aiohttp
from aiohttp import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class BitrixPollingService:
    """
    Сервис для опроса Bitrix24 смарт-процесса.

    Используется планировщиком для получения актуальных данных
    о торговых точках на стадии "Ждём действий клиента".
    """

    def __init__(self):
        self.webhook_url = settings.bitrix_webhook_url

        if not self.webhook_url:
            logger.error("Bitrix webhook URL not configured")

        # ID смарт-процесса "Торговые точки"
        self.entity_type_id = 1070

        # ID воронки
        self.category_id = 38

        # Стадии "Ждём действий клиента" (полный список)
        self.wait_stage_ids = [
            "DT1070_38:UC_70SK2H",  # Чек работы системы
            "DT1070_38:UC_B7P2X4",  # Выведена на MRR
            "DT1070_38:UC_JK4IJR",  # Подключение поставщиков
            "DT1070_38:UC_ILDKHV",  # Ждём действий клиента
            "DT1070_38:UC_IM0YI8",  # Пауза до вывода
            "DT1070_38:UC_NZK4JJ",  # Подключение поставщиков (другая)
            "DT1070_38:UC_XRWEHG",  # Чек работы системы (другая)
            "DT1070_38:UC_9JH4GA",  # Не можем завершить
            "DT1070_38:UC_REJAS2",  # Завершение внедрения
            "DT1070_38:3",          # Не можем завершить (краткая)
        ]

        # Маппинг полей Bitrix (camelCase, как возвращает API)
        self.field_map = {
            'products': 'ufCrm20_1739184606910',      # Продукты
            'telegram_chat': 'ufCrm20_1747732557645',  # Telegram чат
            'wait_reasons': 'ufCrm20_1763475932592',   # Причины ожидания
            'inn': 'ufCrm20_1738855110463',            # ИНН
            'company_name': 'ufCrm20_1744289908193',   # Наименование юр. лица
        }

        # Маппинг продуктов ID -> название
        self.product_id_map = {
            '8426': 'ЕГАИС',
            '8428': 'Накладные',
            '8430': 'ЮЗЭДО',
            '8432': 'Меркурий',
            '8434': 'Маркировка',
        }

    async def get_waiting_items(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Получает все элементы на стадиях ожидания с полной пагинацией.

        Args:
            limit: Максимальное количество элементов (по умолчанию 1000)

        Returns:
            Список элементов
        """
        if not self.webhook_url:
            logger.error("Bitrix webhook URL not configured")
            return []

        url = f"{self.webhook_url}/crm.item.list.json"
        all_items = []
        start = 0
        batch_size = 50  # Bitrix возвращает максимум 50 за раз

        logger.info(f"Starting to fetch waiting items from Bitrix (limit={limit})")

        while start < limit:
            params = {
                "entityTypeId": self.entity_type_id,
                "filter": {"STAGE_ID": self.wait_stage_ids},
                "select": ["id", "title", "stageId", "categoryId"],
                "start": start,
                "limit": batch_size
            }

            try:
                async with aiohttp.ClientSession() as session:
                    json_data = json.dumps(params, ensure_ascii=False)
                    
                    async with session.post(
                        url,
                        data=json_data,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        text = await response.text()
                        
                        if response.status != 200:
                            logger.error(f"Bitrix API error: {response.status} - {text[:200]}")
                            break
                            
                        data = json.loads(text)
                        result = data.get('result', {})
                        items = result.get('items', [])

                        if not items:
                            logger.debug("No more items from Bitrix")
                            break

                        all_items.extend(items)
                        start += len(items)

                        logger.debug(f"Batch {start // batch_size}: got {len(items)} items, total: {len(all_items)}")

                        # Если элементов меньше чем batch_size - это последняя страница
                        if len(items) < batch_size:
                            logger.info(f"Last page reached, total items: {len(all_items)}")
                            break

                        # Небольшая задержка между запросами для избежания rate limiting (2 запроса/сек)
                        await asyncio.sleep(0.5)

            except ClientError as e:
                logger.error(f"Network error fetching items: {e}")
                # Пробуем продолжить с текущими данными
                break
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                break
            except Exception as e:
                logger.exception(f"Unexpected error fetching items: {e}")
                break

        logger.info(f"Found {len(all_items)} items on wait stages")
        return all_items

    async def get_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает полный элемент по ID (с UF-полями).

        Bitrix24 не возвращает UF-поля в crm.item.list,
        поэтому нужно делать отдельный запрос crm.item.get для каждого элемента.
        
        Args:
            item_id: ID элемента
            
        Returns:
            Полный элемент или None
        """
        if not self.webhook_url:
            return None

        url = f"{self.webhook_url}/crm.item.get.json"
        params = {
            "entityTypeId": self.entity_type_id,
            "id": item_id
        }

        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    json_data = json.dumps(params, ensure_ascii=False)
                    
                    async with session.post(
                        url,
                        data=json_data,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        text = await response.text()
                        
                        if response.status != 200:
                            logger.error(f"Bitrix API error ({response.status}): {text[:200]}")
                            return None
                            
                        data = json.loads(text)
                        result = data.get('result', {})
                        item = result.get('item', {})

                        # Проверяем, есть ли данные
                        if item and item.get('id'):
                            logger.debug(f"Got item {item_id}: {item.get('title', '')[:50]}")
                            return item
                        else:
                            logger.warning(f"Item {item_id} not found in Bitrix (empty result)")
                            return None

            except ClientError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Network error (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"Network error after {max_retries} attempts: {e}")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return None
            except Exception as e:
                logger.exception(f"Unexpected error getting item {item_id}: {e}")
                return None

        return None

    async def parse_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Парсит элемент Bitrix в удобный формат.

        Returns:
            Словарь с данными или None если нет Telegram
        """
        # Резолвим Telegram identifier в chat_id
        telegram_chat_id = await self.resolve_and_extract_chat_id(item)

        if not telegram_chat_id:
            logger.debug(f"No valid Telegram chat ID for item {item.get('id')}")
            return None

        return {
            'bitrix_id': item.get('id'),
            'title': item.get('title'),
            'company_name': self.extract_company_name(item),
            'telegram_chat_id': telegram_chat_id,
            'stage_id': item.get('stageId'),
            'wait_reasons': self.extract_wait_reasons(item),
            'product_codes': self.extract_product_codes(item),
            'inn': item.get(self.field_map['inn']),
        }

    def extract_telegram_chat_id(self, item: Dict[str, Any]) -> Optional[int]:
        """
        Извлекает Telegram chat ID из элемента (без резолвинга).

        Возвращает только если это уже числовой ID.
        """
        chat_value = item.get(self.field_map['telegram_chat'])

        if not chat_value:
            return None

        if isinstance(chat_value, int):
            return chat_value

        chat_str = str(chat_value).strip()

        # Если это URL t.me
        if chat_str.startswith("https://t.me/"):
            chat_str = chat_str.replace("https://t.me/", "")

        # Если это @username
        if chat_str.startswith("@"):
            chat_str = chat_str[1:]

        # Пытаемся преобразовать в int
        try:
            return int(chat_str)
        except ValueError:
            return None  # Это username, нужен резолвинг

    async def resolve_and_extract_chat_id(self, item: Dict[str, Any]) -> Optional[int]:
        """
        Извлекает и резолвит Telegram chat_id из элемента Bitrix.

        Сначала пробуем извлечь как обычно, если это username - резолвим через Telegram API.

        Returns:
            Числовой chat_id или None
        """
        chat_value = item.get(self.field_map['telegram_chat'])

        if not chat_value:
            return None

        # Пробуем извлечь как обычно
        chat_id = self.extract_telegram_chat_id(item)

        if chat_id:
            return chat_id  # Уже числовой ID

        # Это username - нужно резолвить
        from app.services.telegram_service import TelegramService

        telegram_service = TelegramService()
        identifier = str(chat_value).strip()

        # Очищаем от префиксов
        if identifier.startswith("https://t.me/"):
            identifier = identifier.replace("https://t.me/", "")
        if identifier.startswith("@"):
            identifier = identifier[1:]

        # Резолвим через Telegram API
        resolved_id = await telegram_service.resolve_telegram_identifier(identifier)

        if resolved_id:
            logger.info(f"Resolved {chat_value} -> {resolved_id}")
            return resolved_id
        else:
            logger.warning(f"Could not resolve Telegram identifier: {chat_value}")
            return None

    def extract_wait_reasons(self, item: Dict[str, Any]) -> List[str]:
        """Извлекает причины ожидания"""
        reasons = item.get(self.field_map['wait_reasons'])

        if not reasons:
            return []

        if isinstance(reasons, list):
            return reasons

        if isinstance(reasons, str):
            return [r.strip() for r in reasons.split(',')]

        return []

    def extract_product_codes(self, item: Dict[str, Any]) -> List[str]:
        """Извлекает коды продуктов"""
        products = item.get(self.field_map['products'])

        if not products:
            return []

        product_codes = []

        if isinstance(products, list):
            for prod_id in products:
                code = self.product_id_map.get(str(prod_id))
                if code:
                    product_codes.append(code)
        elif isinstance(products, str):
            code = self.product_id_map.get(products)
            if code:
                product_codes.append(code)

        return product_codes

    def extract_company_name(self, item: Dict[str, Any]) -> str:
        """Извлекает название компании"""
        # Пробуем из пользовательского поля
        name = item.get(self.field_map['company_name'])
        if name:
            return name

        # Или из заголовка
        return item.get('title', 'Клиент')

    async def search_by_title(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Ищет элементы по ключевому слову в названии.
        
        Args:
            keyword: Ключевое слово для поиска
            limit: Максимальное количество результатов
            
        Returns:
            Список элементов
        """
        if not self.webhook_url:
            return []

        url = f"{self.webhook_url}/crm.item.list.json"
        params = {
            "entityTypeId": self.entity_type_id,
            "filter": {"title": f"%{keyword}%"},
            "select": ["id", "title", "stageId"],
            "limit": limit
        }

        try:
            async with aiohttp.ClientSession() as session:
                json_data = json.dumps(params, ensure_ascii=False)
                
                async with session.post(
                    url,
                    data=json_data,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    text = await response.text()
                    
                    if response.status == 200:
                        data = json.loads(text)
                        result = data.get('result', {})
                        return result.get('items', [])
                    else:
                        logger.error(f"Search error: {text[:200]}")
                        return []

        except Exception as e:
            logger.exception(f"Error searching items: {e}")
            return []
