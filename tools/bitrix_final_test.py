"""Тест интеграции Bitrix24 -> Telegram (рабочая версия)"""
import asyncio
import aiohttp
import os
import sys
from pathlib import Path
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).parent.parent))

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

from app.config import settings


WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")
YOUR_CHAT_ID = 365611506


async def get_waiting_items():
    """Получает элементы на стадии 'Ждём действий клиента'"""
    
    # Стадии "Ждём действий клиента"
    wait_stages = [
        "DT1070_38:UC_70SK2H",  # Чек работы системы
        "DT1070_38:UC_B7P2X4",  # Выведена на MRR
        "DT1070_38:UC_JK4IJR",  # Подключение поставщиков
        "DT1070_38:UC_ILDKHV",  # Ждём действий клиента
    ]
    
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    found_items = []
    
    async with aiohttp.ClientSession() as session:
        for stage_id in wait_stages:
            # Важно: используем data= вместо json= для правильного формата
            params = {
                "entityTypeId": 1070,
                "filter": {"STAGE_ID": stage_id},
                "select": ["ID", "TITLE", "STAGE_ID"],
                "limit": 5
            }
            
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if data.get('result'):
                    items = data['result'].get('items', [])
                    for item in items:
                        if item.get('ID'):  # Проверяем, что ID есть
                            found_items.append(item)
                            print(f"  Найдено: ID={item['ID']}, Title={item.get('TITLE', '')[:50]}")
    
    return found_items


async def send_telegram_message(chat_id: int, text: str):
    """Отправляет сообщение в Telegram"""
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            return data.get("ok"), data


async def main():
    print("="*70)
    print("BITRIX24 -> TELEGRAM: ТЕСТ ИНТЕГРАЦИИ")
    print("="*70)
    
    # 1. Получаем элементы
    print("\n[1] Поиск элементов на стадии 'Ждём действий клиента'...")
    items = await get_waiting_items()
    
    if not items:
        print("\n[WARN] Не найдено элементов с valid ID")
        print("\n[INFO] Отправляем тестовое сообщение с мок-данными...")
        
        test_data = {
            "id": "TEST",
            "title": 'ООО "Тестовая Точка"',
        }
        items = [test_data]
    
    # 2. Отправляем сообщение для первого элемента
    print(f"\n[2] Отправка сообщения для {items[0].get('title', 'N/A')}...")
    
    message = f"""
🔍 <b>{items[0].get('title', 'Клиент')}</b>

Это тестовое сообщение из интеграции Bitrix24.

✅ Статус: Ваша торговая точка находится на стадии внедрения.

⏳ Следующие шаги:
• Заполните все необходимые поля
• Пройдите обучение
• Запустите систему в работу

---
Если вы получили это сообщение — интеграция работает!
"""
    
    success, result = await send_telegram_message(YOUR_CHAT_ID, message)
    
    if success:
        msg_id = result.get('result', {}).get('message_id')
        print(f"\n[OK] Сообщение отправлено! (message_id={msg_id})")
        print(f"Проверьте Telegram чат {YOUR_CHAT_ID}")
    else:
        error = result.get('description', 'Unknown error')
        print(f"\n[ERROR] Ошибка: {error}")
    
    print("\n" + "="*70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
