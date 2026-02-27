"""Поиск ООО Альфа"""
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
    
    # Ищем по названию
    params = {
        "entityTypeId": 1070,
        "filter": {"TITLE": "%Альфа%"},
        "select": ["id", "title", "stageId"],
        "limit": 20
    }
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(url, data=json_data, headers={"Content-Type": "application/json"}) as response:
            text = await response.text()
            data = json.loads(text)
            
            if data.get('result'):
                items = data['result'].get('items', [])
                
                print(f"="*70)
                print(f"NAIDENO KARTOCHEK S 'ALFA' V NAZVANII: {len(items)}")
                print(f"="*70)
                
                for item in items:
                    id = item.get('id')
                    title = item.get('title', '')[:80]
                    stage = item.get('stageId', '')
                    print(f"  ID={id}: {title}")
                    print(f"    Stage: {stage}")
            else:
                print(f"ERROR: {data}")

asyncio.run(main())
