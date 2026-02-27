"""Прямой запрос к Bitrix24 API"""
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


async def main():
    print("="*70)
    print("BITRIX24 API: ПРЯМОЙ ЗАПРОС")
    print("="*70)
    
    # Пробуем получить список смарт-процессов
    url = f"{WEBHOOK_URL}/crmtimeline.item.list.json"
    
    params = {
        "entities": ["DYNAMIC_1070"],
        "limit": 5
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            print(f"\n[1] crmtimeline.item.list.json:")
            print(f"    Status: {response.status}")
            print(f"    Data: {data}")
    
    # Пробуем получить элементы динамического типа
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    params = {
        "entityTypeId": 1070,
        "select": ["ID", "TITLE", "STAGE_ID"],
        "limit": 10
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            print(f"\n[2] crm.item.list.json (Dynamic 1070):")
            print(f"    Status: {response.status}")
            import json
            print(f"    Result: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")


if __name__ == "__main__":
    asyncio.run(main())
