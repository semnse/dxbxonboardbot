"""Проверка последних сообщений бота"""
import asyncio
import os
import sys
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

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


async def main():
    print("="*70)
    print("ПРОВЕРКА ПОСЛЕДНИХ СООБЩЕНИЙ")
    print("="*70)
    
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": 0, "timeout": 1}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            
            if data.get("ok"):
                results = data.get("result", [])
                print(f"\nНайдено сообщений: {len(results)}")
                
                for r in results[-10:]:  # Последние 10
                    if "message" in r:
                        msg = r["message"]
                        chat = msg.get("chat", {})
                        chat_title = chat.get("title", "ЛС")
                        text = msg.get("text", "")[:50]
                        from_user = msg.get("from", {}).get("first_name", "Unknown")
                        
                        print(f"\n  Чат: {chat_title} ({chat.get('id')})")
                        print(f"  От: {from_user}")
                        print(f"  Текст: {text}")
            else:
                print(f"[ERROR] {data}")


if __name__ == "__main__":
    asyncio.run(main())
