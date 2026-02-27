"""
Bitrix24 Smart Process API Client
Работа со смарт-процессом "Торговые точки" (Dynamic Type 1070)
"""
import logging
from typing import Optional, List, Dict, Any

import aiohttp

logger = logging.getLogger(__name__)


class BitrixSmartProcessAPI:
    """
    Клиент для работы со смарт-процессом Bitrix24.
    
    Параметры:
    - entity_type_id: 1070 (Торговые точки)
    - category_id: 38 (воронка)
    - target_stage_id: 3150 (Ждем действий клиента)
    """
    
    def __init__(
        self,
        webhook_url: str,
        entity_type_id: int = 1070,
        category_id: int = 38,
        target_stage_id: str = "3150",
    ):
        self.webhook_url = webhook_url.rstrip('/')
        self.entity_type_id = entity_type_id
        self.category_id = category_id
        self.target_stage_id = target_stage_id
        
        # Маппинг полей (из ответа API)
        self.field_map = {
            'products': 'UF_CRM_20_1739184606910',      # Продукты
            'telegram_chat': 'UF_CRM_20_1747732557645',  # Ссылка на тг-чат
            'wait_reasons': 'UF_CRM_20_1763475932592',   # Ждем действий клиента - причины
            'inn': 'UF_CRM_20_1738855110463',            # ИНН
            'company_name': 'UF_CRM_20_1744289908193',   # Наименование юр. лица
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    # ============================================
    # ЭЛЕМЕНТЫ (Торговые точки)
    # ============================================
    
    async def get_items(
        self,
        filter_params: Optional[Dict] = None,
        select: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Получает список элементов смарт-процесса.
        
        Args:
            filter_params: Фильтр (например, {"STAGE_ID": "3150"})
            select: Поля для выбора
            limit: Лимит записей
        
        Returns:
            Список элементов
        """
        url = f"{self.webhook_url}/crm.item.list.json"
        
        params = {
            "entityTypeId": self.entity_type_id,
            "select": select or ["ID", "TITLE", "STAGE_ID", "CATEGORY_ID"],
            "limit": limit,
        }
        
        if filter_params:
            params["filter"] = filter_params
        
        try:
            session = await self._get_session()
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data.get('result', {}).get('items', [])
                else:
                    logger.error(f"Error getting items: {data}")
                    return []
        
        except Exception as e:
            logger.exception(f"Exception in get_items: {e}")
            return []
    
    async def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает один элемент по ID.
        
        Args:
            item_id: ID элемента
        
        Returns:
            Данные элемента или None
        """
        url = f"{self.webhook_url}/crm.item.get.json"
        
        params = {
            "entityTypeId": self.entity_type_id,
            "id": item_id,
        }
        
        try:
            session = await self._get_session()
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data.get('result')
                else:
                    logger.error(f"Error getting item {item_id}: {data}")
                    return None
        
        except Exception as e:
            logger.exception(f"Exception in get_item: {e}")
            return None
    
    async def get_waiting_items(self) -> List[Dict[str, Any]]:
        """
        Получает все элементы на стадии "Ждем действий клиента" (3150).
        
        Returns:
            Список элементов
        """
        return await self.get_items(
            filter_params={"STAGE_ID": self.target_stage_id},
            select=[
                "ID", "TITLE", "STAGE_ID", "CATEGORY_ID",
                self.field_map['products'],
                self.field_map['telegram_chat'],
                self.field_map['wait_reasons'],
            ],
            limit=100,
        )
    
    # ============================================
    # СТАДИИ
    # ============================================
    
    async def get_status(self, status_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о стадии.
        
        Args:
            status_id: ID стадии (например, "3150")
        
        Returns:
            Данные стадии или None
        """
        url = f"{self.webhook_url}/crm.status.get.json"
        
        params = {"id": status_id}
        
        try:
            session = await self._get_session()
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data.get('result')
                else:
                    logger.error(f"Error getting status {status_id}: {data}")
                    return None
        
        except Exception as e:
            logger.exception(f"Exception in get_status: {e}")
            return None
    
    async def get_status_list(self) -> List[Dict[str, Any]]:
        """
        Получает список всех стадий для нашего смарт-процесса.
        
        Returns:
            Список стадий
        """
        url = f"{self.webhook_url}/crm.statuslist.json"
        
        params = {
            "entityId": f"DYNAMIC_{self.entity_type_id}_STAGE_{self.category_id}"
        }
        
        try:
            session = await self._get_session()
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data.get('result', [])
                else:
                    logger.error(f"Error getting status list: {data}")
                    return []
        
        except Exception as e:
            logger.exception(f"Exception in get_status_list: {e}")
            return []
    
    # ============================================
    # ПОЛЯ
    # ============================================
    
    async def get_fields(self) -> Dict[str, Any]:
        """
        Получает описание всех полей смарт-процесса.
        
        Returns:
            Словарь с описанием полей
        """
        url = f"{self.webhook_url}/crm.item.fields.json"
        
        params = {"entityTypeId": self.entity_type_id}
        
        try:
            session = await self._get_session()
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data.get('result', {}).get('fields', {})
                else:
                    logger.error(f"Error getting fields: {data}")
                    return {}
        
        except Exception as e:
            logger.exception(f"Exception in get_fields: {e}")
            return {}
    
    # ============================================
    # ИЗВЛЕЧЕНИЕ ДАННЫХ
    # ============================================
    
    def extract_telegram_chat_id(self, item: Dict[str, Any]) -> Optional[int]:
        """
        Извлекает Telegram chat ID из элемента.
        
        Форматы:
        - https://t.me/username
        - @username
        - -1001234567890 (ID группы)
        """
        chat_value = item.get(self.field_map['telegram_chat'])
        
        if not chat_value:
            return None
        
        # Если это число (ID группы)
        if isinstance(chat_value, int):
            return chat_value
        
        chat_str = str(chat_value).strip()
        
        # Удаляем префиксы
        if chat_str.startswith("https://t.me/"):
            chat_str = chat_str.replace("https://t.me/", "")
        
        if chat_str.startswith("@"):
            chat_str = chat_str[1:]
        
        # Пытаемся преобразовать в int
        try:
            return int(chat_str)
        except ValueError:
            # Это username, нужно резолвить
            logger.warning(f"Cannot resolve Telegram username: {chat_str}")
            return None
    
    def extract_wait_reasons(self, item: Dict[str, Any]) -> List[str]:
        """
        Извлекает причины ожидания из элемента.
        
        Возвращает список ID значений из мульти-выбора.
        """
        reasons = item.get(self.field_map['wait_reasons'])
        
        if not reasons:
            return []
        
        if isinstance(reasons, list):
            return reasons
        
        if isinstance(reasons, str):
            # Может быть строкой с ID через запятую
            return [r.strip() for r in reasons.split(',')]
        
        return []
    
    def extract_product_codes(self, item: Dict[str, Any]) -> List[str]:
        """
        Извлекает коды продуктов из элемента.
        
        Продукты хранятся как ID значений списка.
        Маппинг ID → код:
        - 8426 → EGAIС
        - 8428 → NAKLADNIE
        - 8430 → YZEDO
        - 8432 → MERCURY
        - 8434 → MARKING
        """
        products = item.get(self.field_map['products'])
        
        if not products:
            return []
        
        # Маппинг ID продуктов из Bitrix
        product_id_map = {
            '8426': 'EGAIС',
            '8428': 'NAKLADNIE',
            '8430': 'YZEDO',
            '8432': 'MERCURY',
            '8434': 'MARKING',
        }
        
        product_codes = []
        
        if isinstance(products, list):
            for prod_id in products:
                code = product_id_map.get(str(prod_id))
                if code:
                    product_codes.append(code)
        elif isinstance(products, str):
            code = product_id_map.get(products)
            if code:
                product_codes.append(code)
        
        return product_codes
    
    def extract_company_name(self, item: Dict[str, Any]) -> str:
        """Извлекает название компании"""
        return item.get('TITLE', 'Клиент')
