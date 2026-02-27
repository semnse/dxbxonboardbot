"""Проверка получения одного элемента - полный вывод"""
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
    url = f"{WEBHOOK_URL}/crm.item.get.json"
    item_id = 5304
    
    params = {
        "entityTypeId": 1070,
        "id": item_id
    }
    
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
                item = data['result'].get('item', {})
                
                print("Полные данные элемента:")
                print(json.dumps(item, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
