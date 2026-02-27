"""
Синхронизация всех карточек Bitrix24 в локальную БД
"""
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
from app.database.models import Client, ChatBinding
from app.database.repository import ClientRepository, ChatBindingRepository
from app.services.bitrix_polling_service import BitrixPollingService
from app.services.bitrix_stage_service import BitrixStageService


async def sync_all_bitrix_items():
    """Синхронизирует все карточки из Bitrix24 в БД"""
    
    print("="*70)
    print("SINHRONIZATSIYA BITRIX24 -> BD")
    print("="*70)
    
    bitrix = BitrixPollingService()
    
    # 1. Poluchaem vse elementy iz Bitrix (bez filtra po stadiyam)
    print("\n[1] Poluchenie vsekh kartochek iz Bitrix24...")
    
    # Получаем элементы со всех стадий
    all_items = await bitrix.get_items(limit=1000)
    
    print(f"    Найдено карточек: {len(all_items)}")
    
    if not all_items:
        print("    [WARN] Нет карточек для синхронизации")
        return
    
    # 2. Sinhroniziruem s BD
    print("\n[2] Sinhronizatsiya s BD...")
    
    async with AsyncSessionLocal() as session:
        client_repo = ClientRepository(session)
        chat_binding_repo = ChatBindingRepository(session)
        
        created = 0
        updated = 0
        skipped = 0
        
        for i, item in enumerate(all_items, 1):
            try:
                bitrix_id = str(item.get('id'))
                title = item.get('title', '')
                stage_id = item.get('stageId', '')
                
                if not bitrix_id:
                    skipped += 1
                    continue
                
                # Poluchaem polnye dannye (s UF-polyami)
                full_item = await bitrix.get_item_by_id(int(bitrix_id))
                
                if not full_item:
                    skipped += 1
                    continue
                
                # Izbekaem dannye
                company_name = full_item.get('title', 'Klient')
                telegram_chat = full_item.get('ufCrm20_1747732557645')
                
                # Rezolvim Telegram
                telegram_id = None
                if telegram_chat:
                    telegram_id = bitrix.extract_telegram_chat_id(full_item)
                    if not telegram_id:
                        # Probujem rezolvit username
                        from app.services.telegram_service import TelegramService
                        tg_service = TelegramService()
                        identifier = str(telegram_chat).strip()
                        if identifier.startswith("https://t.me/"):
                            identifier = identifier.replace("https://t.me/", "")
                        if identifier.startswith("@"):
                            identifier = identifier[1:]
                        telegram_id = await tg_service.resolve_telegram_identifier(identifier)
                
                # Ishchem ili sozdaem klienta
                client = await client_repo.get_by_bitrix_id(bitrix_id)
                
                if not client:
                    # Sozdaem
                    client = Client(
                        bitrix_deal_id=bitrix_id,
                        company_name=company_name,
                        telegram_chat_id=telegram_id,
                        is_active=True,
                    )
                    session.add(client)
                    await session.flush()
                    created += 1
                    
                    if i % 50 == 0:
                        print(f"    Obrabotano: {i}/{len(all_items)} (sozdano: {created})")
                else:
                    # Obnovlyaem
                    if client.telegram_chat_id != telegram_id or client.company_name != company_name:
                        client.telegram_chat_id = telegram_id
                        client.company_name = company_name
                        updated += 1
                    
                    if i % 50 == 0:
                        print(f"    Obrabotano: {i}/{len(all_items)} (obnovleno: {updated})")
                
            except Exception as e:
                print(f"    [ERROR] {bitrix_id}: {e}")
                skipped += 1
        
        # Commit
        await session.commit()
        
        print(f"\n[3] Rezultaty:")
        print(f"    Sozdano: {created}")
        print(f"    Obnovleno: {updated}")
        print(f"    Propushcheno: {skipped}")
    
    # 3. Sozdaem chat_bindings dlya klientov s telegram_chat_id
    print("\n[4] Sozdanie privyazok chatov...")
    
    async with AsyncSessionLocal() as session:
        client_repo = ClientRepository(session)
        chat_binding_repo = ChatBindingRepository(session)
        
        # Poluchaem vsekh klientov s telegram_chat_id
        clients_with_telegram = await client_repo.get_all()
        
        bindings_created = 0
        
        for client in clients_with_telegram:
            if client.telegram_chat_id:
                # Proveryaem, est' li uzhe privyazka
                existing = await chat_binding_repo.get_by_bitrix_deal_id(client.bitrix_deal_id)
                
                if not existing:
                    # Sozdaem privyazku (ispolzuem telegram_chat_id kak chat_id)
                    binding = ChatBinding(
                        chat_id=client.telegram_chat_id,
                        chat_title=f"LS {client.company_name}",
                        bitrix_deal_id=client.bitrix_deal_id,
                        company_name=client.company_name,
                        is_active=True,
                    )
                    session.add(binding)
                    bindings_created += 1
        
        await session.commit()
        
        print(f"    Sozdano privyazok: {bindings_created}")
    
    print("\n" + "="*70)
    print("SINHRONIZATSIYA ZAVERSHENA")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(sync_all_bitrix_items())
