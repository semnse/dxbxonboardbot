"""Тест отправки сообщения в групповой чат"""
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

from app.services.telegram_service import TelegramService


async def main():
    print("="*70)
    print("ТЕСТ ОТПРАВКИ В ГРУППОВОЙ ЧАТ")
    print("="*70)
    
    telegram = TelegramService()
    
    # Пробуем разные форматы chat_id для приватного канала
    # Обычно приватные каналы имеют ID вида -100xxxxxxxxxx
    # Попробуем угадать или вставьте правильный ID
    
    print("\n[INFO] Для приватных каналов нужен числовой ID")
    print("  Обычно начинается с -100")
    print("\n  Варианты:")
    print("  1. Добавьте @getmyid_bot в чат для получения ID")
    print("  2. Вставьте известный ID вручную")
    
    # Пример тестового сообщения
    test_message = """
🔍 <b>Тестовое сообщение для ООО "Вамс"</b>

📋 <b>Данные из Bitrix24:</b>
• ИНН: 7730248656
• Стадия: Ждём действий клиента

⏳ <b>Осталось сделать:</b>
• Провести сопоставление номенклатур
• Заполнить торговый зал

💡 <b>Это важно, потому что:</b>
Без этих шагов вы не сможете передавать чеки в ЕГАИС.
Это может привести к штрафам от Росалкогольрегулирования.

---
<i>Бот онбординга Bitrix24</i>
"""
    
    print("\n[INFO] Введите Chat ID чата (или нажмите Enter для пропуска):")
    chat_id_input = input("Chat ID: ").strip()
    
    if not chat_id_input:
        print("[SKIP] Пропуск")
        return
    
    try:
        chat_id = int(chat_id_input)
    except ValueError:
        print(f"[ERROR] Неверный формат: {chat_id_input}")
        return
    
    print(f"\n[INFO] Отправка сообщения в чат {chat_id}...")
    
    result = await telegram.send_message(chat_id, test_message)
    
    if result.ok:
        print(f"[OK] Сообщение отправлено! (msg_id={result.message_id})")
    else:
        print(f"[ERROR] {result.description}")
        print("\n[INFO] Возможные причины:")
        print("  - Бот не добавлен в чат")
        print("  - У бота нет прав на отправку сообщений")
        print("  - Неверный chat_id")


if __name__ == "__main__":
    asyncio.run(main())
