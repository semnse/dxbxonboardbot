"""Тест Bitrix polling сервиса"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

# Загружаем .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

from app.services.bitrix_polling_service import BitrixPollingService


async def main():
    print("="*70)
    print("ТЕСТ: Bitrix Polling Service")
    print("="*70)
    
    service = BitrixPollingService()
    
    print("\n[1] Получаем элементы на стадиях ожидания...")
    items = await service.get_waiting_items(limit=50)
    
    print(f"\nНайдено элементов: {len(items)}")
    
    if items:
        print("\n[2] Парсим элементы (первые 5):")
        parsed_count = 0
        
        for item in items[:5]:  # Первые 5
            # Выводим сырые данные
            tg_field = item.get('UF_CRM_20_1747732557645', 'NOT_SET')
            print(f"\n  Raw item: id={item.get('id')}, title={item.get('title', '')[:30]}")
            print(f"    Telegram field: {tg_field}")
            
            parsed = service.parse_item(item)
            
            if parsed:
                parsed_count += 1
                print(f"  [OK] ID={parsed['bitrix_id']}")
                print(f"       Компания: {parsed['company_name'][:50]}")
                print(f"       Telegram: {parsed['telegram_chat_id']}")
                print(f"       Причины: {parsed['wait_reasons']}")
                print(f"       Продукты: {parsed['product_codes']}")
            else:
                print(f"  [SKIP] No Telegram chat ID")
        
        print(f"\nИтого распарсено: {parsed_count} из {len(items[:5])}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
