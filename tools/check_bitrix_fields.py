"""Проверка полей Bitrix"""
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
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    # Запрашиваем с конкретными полями
    params = {
        "entityTypeId": 1070,
        "filter": {"STAGE_ID": "DT1070_38:UC_70SK2H"},
        "select": [
            "id",
            "title",
            "uf_crm_20_1747732557645",  # telegram
            "uf_crm_20_1763475932592",  # wait_reasons
        ],
        "limit": 3
    }
    
    print(f"Request: {json.dumps(params, ensure_ascii=False)}\n")
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(
            url,
            data=json_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            text = await response.text()
            data = json.loads(text)
            
            items = data.get('result', {}).get('items', [])
            
            for item in items:
                print(f"Item {item.get('id')}:")
                print(f"  Keys: {list(item.keys())}")
                print(f"  title: {item.get('title', '')[:50]}")
                print(f"  uf_crm_20_1747732557645: {item.get('uf_crm_20_1747732557645')}")
                print(f"  uf_crm_20_1763475932592: {item.get('uf_crm_20_1763475932592')}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
