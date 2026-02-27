"""Проверка получения сообщений ботом"""
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
    print("ПРОВЕРКА СООБЩЕНИЙ БОТА")
    print("="*70)
    
    # 1. Проверяем бота
    url = f"https://api.telegram.org/bot{token}/getMe"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data.get("ok"):
                me = data.get("result", {})
                print(f"\nБот: @{me.get('username')}")
                print(f"ID: {me.get('id')}")
    
    # 2. Проверяем сообщения (сбрасываем offset)
    print("\n[INFO] Проверка сообщений (offset=-1)...")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": -1, "timeout": 1}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            if data.get("ok"):
                results = data.get("result", [])
                print(f"Найдено сообщений: {len(results)}")
                
                if results:
                    for r in results[-5:]:
                        if "message" in r:
                            msg = r["message"]
                            chat_id = msg.get("chat", {}).get("id")
                            text = msg.get("text", "")[:50]
                            from_user = msg.get("from", {}).get("first_name", "Unknown")
                            print(f"  - От {from_user} (chat={chat_id}): {text}")
            else:
                print(f"ERROR: {data}")
    
    # 3. Проверяем, добавлен ли бот в чаты
    print("\n[INFO] Проверка чатов бота...")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    params = {"offset": 0, "timeout": 1, "limit": 10}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            if data.get("ok"):
                results = data.get("result", [])
                chats = set()
                for r in results:
                    if "message" in r:
                        chat = r["message"].get("chat", {})
                        chat_id = chat.get("id")
                        chat_title = chat.get("title", "ЛС")
                        chat_type = chat.get("type", "unknown")
                        chats.add((chat_id, chat_title, chat_type))
                
                if chats:
                    print(f"Бот есть в {len(chats)} чат(а)х:")
                    for chat_id, title, chat_type in chats:
                        print(f"  - {chat_type}: {title} (ID={chat_id})")
                else:
                    print("Бот не получает сообщения из чатов")
            else:
                print(f"ERROR: {data}")

if __name__ == "__main__":
    asyncio.run(main())
