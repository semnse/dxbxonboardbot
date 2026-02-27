"""Просмотр элементов Bitrix24"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import dotenv_values

# Загружаем .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.bitrix_smart_api import BitrixSmartProcessAPI


async def main():
    WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")
    
    if not WEBHOOK_URL:
        print("[ERROR] Webhook URL не настроен")
        return
    
    print("="*70)
    print("BITRIX24: ПРОСМОТР ТОРГОВЫХ ТОЧЕК")
    print("="*70)
    
    api = BitrixSmartProcessAPI(
        webhook_url=WEBHOOK_URL,
        entity_type_id=1070,
        category_id=38,
        target_stage_id="3150",
    )
    
    # Получаем стадии
    print("\n[1] СТАДИИ ВОРОНКИ:")
    statuses = await api.get_status_list()
    for s in statuses[:10]:
        print(f"  - {s.get('NAME', 'N/A')} (ID: {s.get('ID')})")
    
    # Получаем все элементы
    print("\n[2] ВСЕ ТОРГОВЫЕ ТОЧКИ (до 20):")
    all_items = await api.get_items(limit=20)
    
    if not all_items:
        print("  [WARN] Нет элементов")
    else:
        for item in all_items:
            stage_id = item.get('STAGE_ID', 'N/A')
            title = item.get('TITLE', 'N/A')
            item_id = item.get('ID')
            
            # Находим название стадии
            stage_name = next((s.get('NAME') for s in statuses if s.get('ID') == stage_id), 'N/A')
            
            print(f"\n  [{'*' if stage_id == '3150' else ' '}] ID={item_id}")
            print(f"      Название: {title}")
            print(f"      Стадия: {stage_id} ({stage_name})")
            
            # Проверяем Telegram
            telegram = api.extract_telegram_chat_id(item)
            print(f"      Telegram: {telegram or 'не указан'}")
    
    print("\n" + "="*70)
    print("Для создания тестовой точки:")
    print("  1. Откройте Bitrix24 -> Смарт-процессы -> Торговые точки")
    print("  2. Создайте новую точку")
    print("  3. Укажите стадию 'Ждём действий клиента' (3150)")
    print("  4. Заполните поле Telegram чат (ваш ID: 365611506)")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
