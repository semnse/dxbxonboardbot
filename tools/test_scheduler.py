"""
Test command to trigger scheduler manually
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

from app.bot.scheduler import send_daily_reminders


async def main():
    print("="*70)
    print("СИМУЛЯЦИЯ 9:00 МСК - ОТПРАВКА НАПОМИНАНИЙ")
    print("="*70)
    
    print("\n[INFO] Запуск send_daily_reminders()...")
    
    try:
        await send_daily_reminders()
        print("\n[OK] Напоминания отправлены!")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    
    print("\n" + "="*70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
