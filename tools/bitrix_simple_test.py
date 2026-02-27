"""
Тест интеграции Bitrix24 -> Telegram
Отправка сообщения на основе данных из Bitrix
"""
import asyncio
import aiohttp
import os
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

# Загружаем .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

from app.config import settings


# Данные из Bitrix24 (симуляция того, что придет из смарт-процесса)
TEST_DATA = {
    "company_name": 'ООО "Тестовая Точка"',
    "telegram_chat_id": 365611506,  # Ваш chat_id
    "products": ["ЕГАИС", "Меркурий"],
    "wait_reasons": [
        ("Нет УКЭП", "Не сможете подписывать документы УКЭП"),
        ("Не загружен JaCarta", "Риск штрафа при проверке"),
    ]
}


async def send_message():
    # Формируем сообщение
    lines = [
        f"🔍 {TEST_DATA['company_name']}, напоминаем о шагах!",
        "",
        "✅ УЖЕ ДОСТУПНО:",
    ]
    
    for product in TEST_DATA['products']:
        lines.append(f"• {product}")
    
    lines.append("")
    lines.append("⏳ ОСТАЛОСЬ СДЕЛАТЬ:")
    
    for reason, risk in TEST_DATA['wait_reasons']:
        lines.append(f"• {reason} → {risk}")
    
    lines.append("")
    lines.append("---")
    lines.append("Это тестовое сообщение из Bitrix24 интеграции")
    
    message = "\n".join(lines)
    
    # Отправляем в Telegram
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": TEST_DATA['telegram_chat_id'],
        "text": message,
        "parse_mode": "HTML"
    }
    
    print("Sending message to Telegram...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            
            if data.get("ok"):
                msg_id = data['result']['message_id']
                print(f"OK: Message sent! (id={msg_id})")
                return True
            else:
                error = data.get('description', 'Unknown error')
                print(f"ERROR: {error}")
                return False


if __name__ == "__main__":
    result = asyncio.run(send_message())
    print("\nCheck your Telegram!")
    exit(0 if result else 1)
