"""
Telegram Service
Клиент для работы с Telegram Bot API
"""
import logging
from typing import Optional

import aiohttp
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramResponse(BaseModel):
    """Ответ от Telegram Bot API"""

    ok: bool
    message_id: Optional[int] = None
    error_code: Optional[int] = None
    description: Optional[str] = None


class ChatInfo(BaseModel):
    """Информация о чате"""

    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None


class TelegramService:
    """
    Сервис для работы с Telegram Bot API.
    """

    def __init__(self):
        self.token = settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получает или создаёт HTTP сессию"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Закрывает HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
    ) -> TelegramResponse:
        """Отправляет текстовое сообщение"""
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        if disable_notification:
            payload["disable_notification"] = True

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                data = await response.json()

                if response.status == 200 and data.get("ok"):
                    return TelegramResponse(
                        ok=True,
                        message_id=data.get("result", {}).get("message_id"),
                    )
                else:
                    error_desc = data.get("description", "Unknown error")
                    return TelegramResponse(ok=False, description=error_desc)

        except aiohttp.ClientError as e:
            logger.exception(f"Network error sending Telegram message: {e}")
            return TelegramResponse(ok=False, description=str(e))

    async def get_chat_info(self, chat_id: str) -> Optional[ChatInfo]:
        """Получает информацию о чате"""
        url = f"{self.base_url}/getChat"
        params = {"chat_id": chat_id}

        try:
            session = await self._get_session()
            async with session.post(url, json=params) as response:
                data = await response.json()

                if data.get("ok"):
                    result = data.get("result", {})
                    return ChatInfo(
                        id=result.get("id"),
                        type=result.get("type"),
                        title=result.get("title"),
                        username=result.get("username"),
                    )
                else:
                    logger.warning(f"Failed to get chat info: {data.get('description')}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting chat info: {e}")
            return None

    async def resolve_telegram_identifier(self, identifier: str) -> Optional[int]:
        """
        Резолвит Telegram identifier в числовой chat_id.
        
        Поддерживаемые форматы:
        - https://t.me/username
        - https://t.me/+channel_hash
        - @username
        - username
        - -1001234567890 (уже числовой ID)
        
        Returns:
            Числовой chat_id или None если не удалось резолвить
        """
        if not identifier:
            return None
        
        identifier = str(identifier).strip()
        
        # Если это уже числовой ID
        try:
            return int(identifier)
        except ValueError:
            pass
        
        # Если это URL t.me
        if identifier.startswith("https://t.me/"):
            identifier = identifier.replace("https://t.me/", "")
        
        # Если это @username
        if identifier.startswith("@"):
            identifier = identifier[1:]
        
        # Проверяем, не стал ли это числовой ID после очистки
        try:
            return int(identifier)
        except ValueError:
            pass
        
        # Это username - пробуем резолвить через getChat
        logger.info(f"Resolving username: @{identifier}")
        
        try:
            chat_info = await self.get_chat_info(f"@{identifier}")
            if chat_info:
                logger.info(f"Resolved @{identifier} -> {chat_info.id}")
                return chat_info.id
            else:
                logger.warning(f"Failed to resolve username: @{identifier}")
                return None
        except Exception as e:
            logger.exception(f"Error resolving username @{identifier}: {e}")
            return None
