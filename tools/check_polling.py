"""Проверка работы polling"""
import asyncio
import os
import aiohttp
from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

async def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    
    # 1. Проверяем бота
    print("="*70)
    print("PROVERKA BOTA")
    print("="*70)
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data.get("ok"):
                me = data.get("result", {})
                print(f"  Username: @{me.get('username')}")
                print(f"  Name: {me.get('first_name')}")
                print(f"  ID: {me.get('id')}")
            else:
                print(f"ERROR: {data}")
    
    # 2. Проверяем обновления с offset=-1 (сброс)
    print("\n" + "="*70)
    print("PROVERKA SOOBShCHENIY (offset=-1)")
    print("="*70)
    
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": -1, "timeout": 1, "limit": 10}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            if data.get("ok"):
                results = data.get("result", [])
                print(f"  Naideno soobshcheniy: {len(results)}")
                
                if results:
                    for r in results:
                        msg = r.get("message", {})
                        text = msg.get("text", "")[:50]
                        chat = msg.get("chat", {})
                        print(f"    - Chat {chat.get('id')}: {text}")
            else:
                print(f"ERROR: {data}")

asyncio.run(main())
