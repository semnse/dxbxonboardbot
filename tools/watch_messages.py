"""Проверка сообщений в реальном времени"""
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
    print("ПРОВЕРКА СООБЩЕНИЙ В РЕАЛЬНОМ ВРЕМЕНИ")
    print("="*70)
    print("Ожидание сообщений... (10 секунд)")
    print("Напишите /test боту в ЛС или в чат")
    print("="*70)
    
    # Сбрасываем offset и ждём
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    for i in range(10):
        params = {"offset": 0, "timeout": 1, "limit": 10}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                if data.get("ok"):
                    results = data.get("result", [])
                    if results:
                        print(f"\n[{i+1}s] Найдено сообщений: {len(results)}")
                        for r in results:
                            if "message" in r:
                                msg = r["message"]
                                chat = msg.get("chat", {})
                                chat_title = chat.get("title", "ЛС")
                                text = msg.get("text", "")[:50]
                                print(f"  - {chat_title}: {text}")
                    else:
                        print(f"[{i+1}s] Нет новых сообщений")
                else:
                    print(f"[{i+1}s] ERROR: {data}")
        
        await asyncio.sleep(1)
    
    print("\nПроверка завершена")

if __name__ == "__main__":
    asyncio.run(main())
