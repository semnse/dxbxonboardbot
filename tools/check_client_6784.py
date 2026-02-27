"""Проверка карточки в БД"""
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

from app.database.connection import AsyncSessionLocal
from app.database.repository import ClientRepository
from app.database.models import Client


async def main():
    print("="*70)
    print("ПРОВЕРКА КАРТОЧКИ В БД")
    print("="*70)
    
    # Проверяем в БД
    async with AsyncSessionLocal() as session:
        client_repo = ClientRepository(session)
        
        # Ищем по bitrix_deal_id
        client = await client_repo.get_by_bitrix_id("6784")
        
        if client:
            print(f"\n[OK] КАРТОЧКА НАЙДЕНА В БД!")
            print(f"  ID: {client.id}")
            print(f"  Bitrix ID: {client.bitrix_deal_id}")
            print(f"  Компания: {client.company_name}")
            print(f"  Telegram: {client.telegram_chat_id}")
            print(f"  Активна: {client.is_active}")
        else:
            print(f"\n[WARN] КАРТОЧКА НЕ НАЙДЕНА В БД")
            print(f"  Bitrix ID: 6784")
            print(f"\n[INFO] Это нормально - карточка будет создана при команде /add 6784")
    
    # Проверяем в Bitrix24
    print("\n[INFO] Проверка в Bitrix24...")
    
    from app.services.bitrix_polling_service import BitrixPollingService
    
    bitrix = BitrixPollingService()
    full_item = await bitrix.get_item_by_id(6784)
    
    if full_item:
        print(f"[OK] КАРТОЧКА НАЙДЕНА В BITRIX24!")
        print(f"  ID: {full_item.get('id')}")
        print(f"  Title: {full_item.get('title', '')[:80]}")
        print(f"  Stage: {full_item.get('stageId')}")
        
        # Проверяем Telegram
        telegram = full_item.get('ufCrm20_1747732557645')
        print(f"  Telegram: {telegram}")
    else:
        print(f"[ERROR] КАРТОЧКА НЕ НАЙДЕНА В BITRIX24")


if __name__ == "__main__":
    asyncio.run(main())
