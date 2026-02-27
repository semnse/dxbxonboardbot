"""Проверка categoryId у карточек"""
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
    url = base_url + '/crm.item.list.json'
    
    # Без фильтра - получаем все
    params = {
        "entityTypeId": 1070,
        "select": ["id", "title", "stageId", "categoryId"],
        "limit": 100
    }
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(url, data=json_data, headers={"Content-Type": "application/json"}) as response:
            text = await response.text()
            data = json.loads(text)
            
            if data.get('result'):
                items = data['result'].get('items', [])
                
                # Группируем по categoryId
                by_category = {}
                for item in items:
                    cat_id = str(item.get('categoryId', 'UNKNOWN'))
                    if cat_id not in by_category:
                        by_category[cat_id] = []
                    by_category[cat_id].append(item)
                
                print(f"="*70)
                print(f"RAZBIVKA PO VORONKAM (categoryId):")
                print(f"="*70)
                
                for cat_id, cat_items in sorted(by_category.items()):
                    print(f"\n  CATEGORY_ID: {cat_id} ({len(cat_items)} kartochek)")
                    for item in cat_items[:3]:
                        title = item.get('title', '')[:50]
                        stage = item.get('stageId', '')
                        print(f"    - ID={item.get('id')}: {title} (stage={stage})")
                    if len(cat_items) > 3:
                        print(f"    ... i eshche {len(cat_items) - 3}")

asyncio.run(main())
