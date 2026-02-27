"""Проверка подключения к БД"""
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

async def main():
    print("="*70)
    print("ПРОВЕРКА ПОДКЛЮЧЕНИЯ К БД")
    print("="*70)
    
    from app.database.connection import AsyncSessionLocal
    from sqlalchemy import text
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            print("\n[OK] БД подключена!")
            
            # Проверяем таблицу chat_bindings
            from app.database.models import ChatBinding
            result = await session.execute(text("SELECT COUNT(*) FROM chat_bindings"))
            count = result.scalar()
            print(f"    chat_bindings: {count} записей")
            
    except Exception as e:
        print(f"\n[ERROR] БД не подключена: {e}")

if __name__ == "__main__":
    asyncio.run(main())
