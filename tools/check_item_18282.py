"""Проверка карточки 18282"""
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
    params = {'entityTypeId': 1070, 'id': 18282}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            
            if data.get('result'):
                item = data['result']
                print(f"ID: {item.get('id')}")
                print(f"Title: {item.get('title', '')[:100]}")
                print(f"Stage: {item.get('stageId')}")
            else:
                print(f"NOT FOUND")
                print(f"Error: {data}")

asyncio.run(main())
