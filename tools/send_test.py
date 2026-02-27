"""Отправка тестового сообщения"""
import asyncio
import aiohttp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


async def send_test():
    chat_id = 365611506
    token = settings.telegram_bot_token
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    message = """
🔍 <b>Тестовое сообщение от бота онбординга</b>

✅ УЖЕ ДОСТУПНО:
• Приём алкогольных накладных в ЕГАИС
• Просмотр остатков по пиву

⏳ ОСТАЛОСЬ СДЕЛАТЬ:
• Нет УКЭП → Не сможете подписывать документы юридически значимой подписью
• Не загружен сертификат JaCarta → Не сможете отправлять документы в ЕГАИС

💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:
Без этих шагов вы не сможете легально работать с алкоголем. Это может привести к штрафам от контролирующих органов.

---
Это тестовое сообщение. Если вы его видите — бот работает! ✅
"""
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    print(f"Отправка сообщения в чат {chat_id}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            
            if response.status == 200 and data.get("ok"):
                print(f"OK: Сообщение отправлено! (message_id={data['result']['message_id']})")
                return True
            else:
                print(f"ERROR: {data.get('error_code')} - {data.get('description')}")
                return False


if __name__ == "__main__":
    result = asyncio.run(send_test())
    sys.exit(0 if result else 1)
