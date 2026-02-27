"""Проверка получения одного элемента с UF-полями"""
import asyncio
import os
import json
from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

import aiohttp

WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")

async def main():
    print("="*70)
    print("BITRIX24: ПРОВЕРКА crm.item.get")
    print("="*70)
    
    # Получаем один элемент через crm.item.get
    url = f"{WEBHOOK_URL}/crm.item.get.json"
    
    # ID элемента из предыдущих запросов
    item_id = 5304
    
    params = {
        "entityTypeId": 1070,
        "id": item_id
    }
    
    print(f"\nЗапрос элемента ID={item_id}...")
    print(f"URL: {url}")
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            text = await response.text()
            data = json.loads(text)
            
            if data.get('result'):
                item = data['result']
                print(f"\n[OK] Получен элемент:")
                print(f"  ID: {item.get('id')}")
                print(f"  TITLE: {item.get('title', '')[:60]}")
                print(f"  STAGE_ID: {item.get('stageId')}")
                
                # Проверяем все UF-поля
                print(f"\n  UF-поля:")
                uf_fields = {
                    'telegram': 'uf_crm_20_1747732557645',
                    'wait_reasons': 'uf_crm_20_1763475932592',
                    'products': 'uf_crm_20_1739184606910',
                    'inn': 'uf_crm_20_1738855110463',
                    'company_name': 'uf_crm_20_1744289908193',
                }
                
                for name, field in uf_fields.items():
                    value = item.get(field)
                    print(f"    {field}: {value}")
                
                # Показываем ВСЕ ключи элемента
                print(f"\n  ВСЕ ключи элемента:")
                for key in sorted(item.keys()):
                    if key != 'result':
                        print(f"    {key}: {str(item[key])[:100]}")
            else:
                print(f"\n[ERROR] {data}")


if __name__ == "__main__":
    asyncio.run(main())
