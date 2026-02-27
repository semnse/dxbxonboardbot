"""Проверка карточки 6784 в Bitrix24"""
import asyncio
import os
import json
import aiohttp
from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

async def main():
    base_url = os.environ.get('BITRIX_WEBHOOK_URL', '').rstrip('/')
    url = base_url + '/crm.item.get.json'
    
    params = {'entityTypeId': 1070, 'id': 6784}
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(url, data=json_data, headers={"Content-Type": "application/json"}) as response:
            text = await response.text()
            data = json.loads(text)
            
            if data.get('result'):
                result = data['result']
                print(f"Result keys: {list(result.keys())}")
                
                item = result.get('item', {})
                print(f"Item keys: {list(item.keys())[:10]}...")
                
                if item and item.get('id'):
                    print(f"="*70)
                    print(f"KARTOCHKA NAIDENA V BITRIX24!")
                    print(f"="*70)
                    print(f"  ID: {item.get('id')}")
                    print(f"  Title: {item.get('title', '')[:100]}")
                    print(f"  Stage: {item.get('stageId')}")
                    print(f"  Category: {item.get('categoryId')}")
                    
                    # UF-поля
                    print(f"\n  UF-поля:")
                    print(f"    Telegram: {item.get('ufCrm20_1747732557645')}")
                    print(f"    INN: {item.get('ufCrm20_1738855110463')}")
                    print(f"    Produkty: {item.get('ufCrm20_1739184606910')}")
                    print(f"    Prichiny: {item.get('ufCrm20_1763475932592')}")
                else:
                    print(f"="*70)
                    print(f"ITEM PUSTOY!")
                    print(f"="*70)
                    print(f"Full item: {item}")
            else:
                print(f"="*70)
                print(f"RESULT PUSTOY!")
                print(f"="*70)
                print(f"Full data: {data}")

asyncio.run(main())
