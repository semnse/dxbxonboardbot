"""Проверка подключения к БД и клиентов"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal
from app.database.models import Client, DealState


async def check_db():
    print("="*70)
    print("ПРОВЕРКА БАЗЫ ДАННЫХ")
    print("="*70)
    
    try:
        async with AsyncSessionLocal() as session:
            # Проверяем клиентов
            from sqlalchemy import select
            result = await session.execute(select(Client))
            clients = result.scalars().all()
            
            print(f"\n[INFO] Найдено клиентов: {len(clients)}")
            
            for client in clients[:5]:
                print(f"  - ID={client.id}, Компания: {client.company_name}, "
                      f"Telegram: {client.telegram_chat_id or 'не указан'}")
            
            # Проверяем deal states
            result = await session.execute(select(DealState))
            states = result.scalars().all()
            
            print(f"\n[INFO] Найдено состояний сделок: {len(states)}")
            
            active_states = [s for s in states if s.is_bot_active]
            print(f"  Из них активных (бот включен): {len(active_states)}")
            
            if clients:
                print("\n[OK] База данных подключена и содержит данные")
                return clients
            else:
                print("\n[WARN] База данных пуста")
                return []
                
    except Exception as e:
        print(f"\n[ERROR] Ошибка подключения к БД: {e}")
        print("   Убедитесь, что PostgreSQL запущен")
        return []


if __name__ == "__main__":
    asyncio.run(check_db())
