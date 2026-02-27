"""Простое получение списка всех карточек из Bitrix24"""
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
    
    params = {
        "entityTypeId": 1070,
        "filter": {"CATEGORY_ID": "38"},  # Воронка "Торговые точки" (отдел внедрения)
        "select": ["id", "title", "stageId", "categoryId"],
        "limit": 600
    }
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(url, data=json_data, headers={"Content-Type": "application/json"}) as response:
            text = await response.text()
            data = json.loads(text)
            
            if data.get('result'):
                items = data['result'].get('items', [])
                total = data['result'].get('total', len(items))
                
                print(f"="*70)
                print(f"NAIDENO KARTOCHEK: {len(items)} (total: {total})")
                print(f"="*70)
                
                # Pokazyvaem pervye 20
                for item in items[:20]:
                    print(f"  ID={item.get('id')}: {item.get('title', '')[:60]}")
                
                if len(items) > 20:
                    print(f"  ... i eshche {len(items) - 20}")
            else:
                print(f"ERROR: {data}")

asyncio.run(main())
