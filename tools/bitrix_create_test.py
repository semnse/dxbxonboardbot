"""Создание тестовой торговой точки в Bitrix24"""
import asyncio
import aiohttp
import os
from pathlib import Path
from dotenv import dotenv_values

# Загружаем .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")

# Ваш Telegram Chat ID
TELEGRAM_CHAT_ID = 365611506


async def main():
    print("="*70)
    print("BITRIX24: СОЗДАНИЕ ТЕСТОВОЙ ТОРГОВОЙ ТОЧКИ")
    print("="*70)
    
    url = f"{WEBHOOK_URL}/crm.item.add.json"
    
    # Данные для создания
    fields = {
        "entityTypeId": 1070,
        "fields": {
            "TITLE": f"Тестовая ТТ - {TELEGRAM_CHAT_ID}",
            "CATEGORY_ID": "38",  # Воронка
            "STAGE_ID": "DT1070_38:3150",  # Стадия "Ждём действий клиента"
            
            # Telegram чат
            "UF_CRM_20_1747732557645": str(TELEGRAM_CHAT_ID),
            
            # Причины ожидания (NO_UKEP, NO_JACARTA)
            "UF_CRM_20_1763475932592": ["NO_UKEP", "NO_JACARTA"],
            
            # Продукты (ЕГАИС, Меркурий)
            "UF_CRM_20_1739184606910": ["8426", "8432"],  # ЕГАИС=8426, MERCURY=8432
        }
    }
    
    print(f"\n[INFO] Создание элемента...")
    print(f"  Title: Тестовая ТТ - {TELEGRAM_CHAT_ID}")
    print(f"  Stage: DT1070_38:3150 (Ждём действий клиента)")
    print(f"  Telegram: {TELEGRAM_CHAT_ID}")
    print(f"  Причины: NO_UKEP, NO_JACARTA")
    print(f"  Продукты: ЕГАИС, MERCURY")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=fields) as response:
            data = await response.json()
            
            if response.status == 200 and data.get('result'):
                item_id = data.get('result')
                print(f"\n[OK] Элемент создан! ID: {item_id}")
                print(f"\n[INFO] Откройте в Bitrix24:")
                print(f"  https://docsinbox.bitrix24.ru/company/personal/user/100398/crm/leader/1070/{item_id}/")
            else:
                print(f"\n[ERROR] Ошибка создания:")
                print(f"  {data}")


if __name__ == "__main__":
    asyncio.run(main())
