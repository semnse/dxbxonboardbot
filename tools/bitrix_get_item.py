"""Получение конкретного элемента по ID"""
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

WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")


async def main():
    print("="*70)
    print("BITRIX24: ПОЛУЧЕНИЕ ЭЛЕМЕНТА ПО ID")
    print("="*70)
    
    # Сначала получим список и возьмем первый ID
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    params = {
        "entityTypeId": 1070,
        "filter": {"STAGE_ID": "DT1070_38:UC_70SK2H"},
        "select": ["ID"],
        "limit": 1
    }
    
    print("\n[1] Получаем ID первого элемента...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            
            if data.get('result'):
                items = data['result'].get('items', [])
                if items:
                    item_id = items[0].get('ID')
                    print(f"  ID элемента: {item_id}")
                    
                    # Теперь получаем полный элемент
                    print(f"\n[2] Получаем полный элемент {item_id}...")
                    
                    get_url = f"{WEBHOOK_URL}/crm.item.get.json"
                    get_params = {
                        "entityTypeId": 1070,
                        "id": item_id
                    }
                    
                    async with session.post(get_url, json=get_params) as get_response:
                        get_data = await get_response.json()
                        
                        if get_data.get('result'):
                            item = get_data['result']
                            print(f"\n  ДАННЫЕ ЭЛЕМЕНТА:")
                            print(f"    ID: {item.get('ID')}")
                            print(f"    TITLE: {item.get('TITLE', '')[:60]}")
                            print(f"    STAGE_ID: {item.get('STAGE_ID')}")
                            
                            # Проверяем пользовательские поля
                            print(f"\n  ПОЛЯ:")
                            for key, value in item.items():
                                if key.startswith('UF_'):
                                    print(f"    {key}: {value}")
                        else:
                            print(f"  [ERROR] {get_data}")
                else:
                    print("  [EMPTY] Нет элементов")
            else:
                print(f"  [ERROR] {data}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
