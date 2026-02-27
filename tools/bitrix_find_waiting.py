"""Поиск элементов на стадии ожидания"""
import asyncio
import aiohttp
import os
import json
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
    print("BITRIX24: ПОИСК ЭЛЕМЕНТОВ НА СТАДИИ 3150")
    print("="*70)
    
    # Получаем элементы на стадии 3150
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    # Пробуем разные варианты фильтра
    filters = [
        {"STAGE_ID": "3150"},
        {"STAGE_ID": "DT1070_38:3150"},
        {"=STAGE_ID": "3150"},
    ]
    
    for i, filter_params in enumerate(filters, 1):
        print(f"\n[Попытка {i}]: Фильтр {filter_params}")
        
        params = {
            "entityTypeId": 1070,
            "filter": filter_params,
            "select": [
                "ID", "TITLE", "STAGE_ID", "CATEGORY_ID",
                "UF_CRM_20_1739184606910",      # products
                "UF_CRM_20_1747732557645",      # telegram_chat
                "UF_CRM_20_1763475932592",      # wait_reasons
            ],
            "limit": 10
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if response.status == 200:
                    items = data.get('result', {}).get('items', [])
                    if items:
                        print(f"  [OK] Найдено элементов: {len(items)}")
                        for item in items:
                            print(f"\n    ID: {item.get('ID')}")
                            print(f"    Название: {item.get('TITLE')}")
                            print(f"    Стадия: {item.get('STAGE_ID')}")
                    else:
                        print(f"  [WARN] Нет элементов с таким фильтром")
                else:
                    print(f"  [ERROR] {data}")
    
    # Показываем все элементы для понимания
    print("\n" + "="*70)
    print("ВСЕ ЭЛЕМЕНТЫ (для понимания структуры):")
    print("="*70)
    
    params = {
        "entityTypeId": 1070,
        "select": ["ID", "TITLE", "STAGE_ID"],
        "limit": 5
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            items = data.get('result', {}).get('items', [])
            
            for item in items:
                print(f"\n  ID={item.get('ID')}: {item.get('TITLE')[:50]}")
                print(f"    Стадия: {item.get('STAGE_ID')}")


if __name__ == "__main__":
    asyncio.run(main())
