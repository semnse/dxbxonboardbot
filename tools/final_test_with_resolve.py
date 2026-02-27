"""
Финальный тест интеграции Bitrix24 -> Telegram с резолвингом
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

from app.services.bitrix_polling_service import BitrixPollingService
from app.services.telegram_service import TelegramService


async def main():
    print("="*70)
    print("ФИНАЛЬНЫЙ ТЕСТ: Bitrix24 -> Telegram (с резолвингом)")
    print("="*70)
    
    polling = BitrixPollingService()
    telegram = TelegramService()
    
    # 1. Получаем элементы из Bitrix
    print("\n[1] Опрос Bitrix24...")
    items = await polling.get_waiting_items(limit=10)
    print(f"    Найдено элементов: {len(items)}")
    
    if not items:
        print("\n[WARN] Нет элементов на стадиях ожидания")
        return
    
    # 2. Получаем полный элемент и парсим
    print("\n[2] Получение полных данных и резолвинг Telegram...")
    
    for item in items[:3]:  # Первые 3
        print(f"\n    Элемент ID={item.get('id')}...")
        
        # Получаем полный элемент с UF-полями
        full_item = await polling.get_item_by_id(item['id'])
        if not full_item:
            print(f"      [SKIP] Не удалось получить полные данные")
            continue
        
        # Парсим с резолвингом
        parsed = await polling.parse_item(full_item)
        
        if parsed:
            print(f"      [OK] Распаршено:")
            print(f"           Компания: {parsed['company_name'][:50]}")
            print(f"           Telegram: {parsed['telegram_chat_id']}")
            print(f"           Продукты: {parsed['product_codes']}")
        else:
            print(f"      [SKIP] Нет Telegram или не удалось резолвить")
    
    # 3. Отправляем тестовое сообщение
    print("\n[3] Отправка тестового сообщения...")
    
    # Ваш chat_id для теста
    YOUR_CHAT_ID = 365611506
    
    message = """
🔍 <b>Тест интеграции Bitrix24 → Telegram</b>

✅ Резолвинг работает!

Если вы видите это сообщение — бот успешно:
1. Опросил Bitrix24
2. Получил элемент с UF-полями
3. Распарсил Telegram identifier
4. Отправил сообщение

---
<i>Бот онбординга</i>
"""
    
    result = await telegram.send_message(YOUR_CHAT_ID, message)
    
    if result.ok:
        print(f"    [OK] Сообщение отправлено (msg_id={result.message_id})")
    else:
        print(f"    [ERROR] {result.description}")
    
    print("\n" + "="*70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("="*70)
    
    print("\n[INFO] Архитектура интеграции:")
    print("  1. Scheduler (9:00 МСК) -> BitrixPollingService.get_waiting_items()")
    print("  2. Для каждого элемента -> get_item_by_id() (полные данные с UF)")
    print("  3. parse_item() -> resolve_and_extract_chat_id()")
    print("  4. TelegramService.resolve_telegram_identifier() -> chat_id")
    print("  5. Синхронизация с БД -> отправка напоминания")


if __name__ == "__main__":
    asyncio.run(main())
