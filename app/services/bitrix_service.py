"""
Сервис интеграции с Bitrix24
REST API клиент для получения данных из Bitrix
"""
import logging
from typing import Optional, List, Dict, Any

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


class BitrixService:
    """
    Сервис для работы с Bitrix24 API.
    
    Методы:
    - get_deal(): Получение данных сделки
    - get_deals_by_stage(): Сделки на определённой стадии
    - sync_clients(): Синхронизация клиентов
    """
    
    def __init__(self):
        self.webhook_url = settings.bitrix_webhook_url
        self.access_token = settings.bitrix_oauth_access_token
        
        if not self.webhook_url and not self.access_token:
            logger.warning("Bitrix credentials not configured")
    
    async def get_deal(self, deal_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные сделки по ID.
        
        GET /crm.deal.get
        """
        if not self.webhook_url:
            logger.error("Bitrix webhook URL not configured")
            return None
        
        url = f"{self.webhook_url}/crm.deal.get"
        params = {"id": deal_id}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params) as response:
                    data = await response.json()
                    return data.get("result")
        except Exception as e:
            logger.exception(f"Error getting deal from Bitrix: {e}")
            return None
    
    async def get_deals_by_stage(
        self,
        stage_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Получает сделки по стадии.
        
        GET /crm.deal.list
        """
        if not self.webhook_url:
            logger.error("Bitrix webhook URL not configured")
            return []
        
        url = f"{self.webhook_url}/crm.deal.list"
        params = {
            "filter": {"STAGE_ID": stage_id},
            "select": [
                "ID", "TITLE", "STAGE_ID", "COMPANY_TITLE",
                "UF_CRM_WAIT_REASONS", "UF_CRM_TELEGRAM_CHAT",
            ],
            "order": {"ID": "ASC"},
            "limit": limit,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params) as response:
                    data = await response.json()
                    return data.get("result", [])
        except Exception as e:
            logger.exception(f"Error getting deals from Bitrix: {e}")
            return []
    
    async def update_deal(self, deal_id: str, fields: Dict[str, Any]) -> bool:
        """
        Обновляет сделку.
        
        POST /crm.deal.update
        """
        if not self.webhook_url:
            logger.error("Bitrix webhook URL not configured")
            return False
        
        url = f"{self.webhook_url}/crm.deal.update"
        params = {
            "id": deal_id,
            "fields": fields,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params) as response:
                    data = await response.json()
                    return data.get("result", False)
        except Exception as e:
            logger.exception(f"Error updating deal in Bitrix: {e}")
            return False
    
    async def add_comment_to_deal(
        self,
        deal_id: str,
        comment: str,
    ) -> bool:
        """
        Добавляет комментарий к сделке.
        """
        # Получаем текущий комментарий
        deal = await self.get_deal(deal_id)
        if not deal:
            return False
        
        current_comment = deal.get("COMMENTS", "") or ""
        new_comment = f"{current_comment}\n\n[Bot] {comment}" if current_comment else f"[Bot] {comment}"
        
        return await self.update_deal(deal_id, {"COMMENTS": new_comment})
