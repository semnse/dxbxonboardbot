"""Проверка подключения бота к Telegram"""
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

from app.bot.commands import bot


async def main():
    print("="*70)
    print("ПРОВЕРКА ПОДКЛЮЧЕНИЯ БОТА К TELEGRAM")
    print("="*70)
    
    try:
        me = await bot.get_me()
        print(f"\n[OK] Бот подключен!")
        print(f"  Username: @{me.username}")
        print(f"  Name: {me.first_name}")
        print(f"  ID: {me.id}")
        
        # Проверяем обновления
        print("\n[INFO] Проверка обновлений...")
        updates = await bot.get_updates(offset=0, timeout=5)
        print(f"  Найдено обновлений: {len(updates)}")
        
        if updates:
            for update in updates[-5:]:  # Последние 5
                if update.message:
                    print(f"    - Message from {update.message.from_user.first_name}: {update.message.text[:50]}")
        
        await bot.session.close()
        
    except Exception as e:
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    asyncio.run(main())
