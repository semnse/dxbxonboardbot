"""Проверка последних сообщений"""
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
    
    print("="*70)
    print("ПРОВЕРКА ПОСЛЕДНИХ СООБЩЕНИЙ")
    print("="*70)
    
    # Проверяем с offset=0 (все непрочитанные)
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": 0, "timeout": 1, "limit": 20}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            if data.get("ok"):
                results = data.get("result", [])
                print(f"Найдено сообщений: {len(results)}\n")
                
                for r in results:
                    if "message" in r:
                        msg = r["message"]
                        chat_id = msg.get("chat", {}).get("id")
                        chat_title = msg.get("chat", {}).get("title", "ЛС")
                        chat_type = msg.get("chat", {}).get("type", "private")
                        text = msg.get("text", "")[:50]
                        from_user = msg.get("from", {}).get("first_name", "Unknown")
                        print(f"  [{chat_type}] {chat_title} (ID={chat_id})")
                        print(f"    От: {from_user}")
                        print(f"    Текст: {text}")
                        print()
            else:
                print(f"ERROR: {data}")

if __name__ == "__main__":
    asyncio.run(main())
