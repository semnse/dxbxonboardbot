"""Тест резолвинга Telegram username"""
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
    print("ТЕСТ: Резолвинг Telegram username")
    print("="*70)
    
    service = TelegramService()
    
    # Тестовые идентификаторы
    test_identifiers = [
        "365611506",  # Числовой ID
        "+P25JCUFNbKgyNzdi",  # Username из Bitrix
        "@durov",  # Известный username
        "https://t.me/telegram",  # URL
    ]
    
    for identifier in test_identifiers:
        print(f"\n[INFO] Резолвинг: {identifier}")
        chat_id = await service.resolve_telegram_identifier(identifier)
        
        if chat_id:
            print(f"  [OK]Resolved -> {chat_id}")
            
            # Проверяем информацию о чате
            chat_info = await service.get_chat_info(chat_id)
            if chat_info:
                print(f"       Chat: {chat_info.title or chat_info.username}")
                print(f"       Type: {chat_info.type}")
        else:
            print(f"  [SKIP] Не удалось резолвить")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
