"""Получение информации о чате"""
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
    print("ПОЛУЧЕНИЕ CHAT_ID ГРУППЫ")
    print("="*70)
    
    telegram = TelegramService()
    
    # Пробуем разные варианты
    chat_identifiers = [
        "+6niSWiGpkQhhY2My",  # Invite link
        "https://t.me/+6niSWiGpkQhhY2My",  # Full link
    ]
    
    for identifier in chat_identifiers:
        print(f"\n[INFO] Попытка: {identifier}")
        chat_id = await telegram.resolve_telegram_identifier(identifier)
        
        if chat_id:
            print(f"    [OK] Chat ID: {chat_id}")
            
            # Получаем полную информацию
            chat_info = await telegram.get_chat_info(chat_id)
            if chat_info:
                print(f"    Title: {chat_info.title}")
                print(f"    Type: {chat_info.type}")
                print(f"    Username: {chat_info.username}")
            return chat_id
        else:
            print(f"    [SKIP] Не удалось резолвить")
    
    print("\n[WARN] Не удалось получить chat_id")
    print("\n[INFO] Альтернативный способ:")
    print("  1. Добавьте бота @getmyid_bot в ваш чат")
    print("  2. Он покажет ID чата")
    print("  3. Или перешлите сообщение из чата боту @userinfobot")
    return None


if __name__ == "__main__":
    chat_id = asyncio.run(main())
    
    if chat_id:
        print(f"\n{'='*70}")
        print(f"CHAT_ID: {chat_id}")
        print(f"{'='*70}")
