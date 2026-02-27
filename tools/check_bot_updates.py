"""Проверка последних сообщений от бота"""
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
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    # Получаем последние 10 сообщений
    params = {"offset": 0, "timeout": 1, "limit": 10}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            text = await response.text()
            data = await response.json()
            
            if data.get("ok"):
                results = data.get("result", [])
                print(f"="*70)
                print(f"NAIDENO SOOBShCHENIY: {len(results)}")
                print(f"="*70)
                
                for r in results[-5:]:  # Последние 5
                    if "message" in r:
                        msg = r["message"]
                        chat_id = msg.get("chat", {}).get("id")
                        chat_title = msg.get("chat", {}).get("title", "LS")
                        text_msg = msg.get("text", "")[:50]
                        from_user = msg.get("from", {}).get("first_name", "Unknown")
                        
                        print(f"\n  Chat: {chat_title} ({chat_id})")
                        print(f"  Ot: {from_user}")
                        print(f"  Tekst: {text_msg}")
            else:
                print(f"ERROR: {data}")

asyncio.run(main())
