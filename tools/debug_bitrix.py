"""Отладка Bitrix polling"""
import asyncio
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
    print("ОТЛАДКА: Запрос к Bitrix24")
    print("="*70)
    
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    stage_id = "DT1070_38:UC_70SK2H"
    
    params = {
        "entityTypeId": 1070,
        "filter": {"STAGE_ID": stage_id},
        "select": ["ID", "TITLE", "STAGE_ID"],
        "limit": 5
    }
    
    print(f"\nURL: {url}")
    print(f"Stage: {stage_id}")
    print(f"Params: {json.dumps(params, ensure_ascii=False)}")
    
    # Пробуем два способа отправки
    async with aiohttp.ClientSession() as session:
        # Способ 1: json=
        print("\n[1] Тест с json=...")
        async with session.post(url, json=params) as response:
            text = await response.text()
            print(f"    Status: {response.status}")
            print(f"    Response: {text[:200]}")
            
            data = json.loads(text)
            items = data.get('result', {}).get('items', [])
            valid = [i for i in items if i.get('ID')]
            print(f"    Valid items: {len(valid)}")
        
        # Способ 2: data= + json.dumps
        print("\n[2] Тест с data=json.dumps()...")
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            text = await response.text()
            print(f"    Status: {response.status}")
            print(f"    Response: {text[:200]}")
            
            data = json.loads(text)
            items = data.get('result', {}).get('items', [])
            valid = [i for i in items if i.get('ID')]
            print(f"    Valid items: {len(valid)}")


if __name__ == "__main__":
    asyncio.run(main())
