"""
Простой тест системы онбординга
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.bot.message_builder import MessageBuilder


def test_config():
    """Тест конфигурации"""
    print("\n" + "="*70)
    print("ТЕСТ 1: КОНФИГУРАЦИЯ")
    print("="*70)
    
    print(f"TELEGRAM_BOT_TOKEN: {'Настроен' if settings.telegram_bot_token and settings.telegram_bot_token != 'your_bot_token_here' else 'Не настроен'}")
    print(f"BITRIX_WEBHOOK_URL: {'Настроен' if settings.bitrix_webhook_url else 'Не настроен'}")
    print(f"DATABASE_URL: {'Настроен' if settings.database_url else 'Не настроен'}")
    print(f"TIMEZONE: {settings.timezone}")
    
    return settings.telegram_bot_token and settings.telegram_bot_token != 'your_bot_token_here'


def test_message_builder():
    """Тест сборщика сообщений"""
    print("\n" + "="*70)
    print("ТЕСТ 2: СБОРЩИК СООБЩЕНИЙ")
    print("="*70)
    
    builder = MessageBuilder()
    
    from app.database.models import Client
    client = Client(
        id=1,
        bitrix_deal_id="TEST_123",
        company_name='OOO "Test"',
        telegram_chat_id=-1001234567890,
    )
    
    features = [
        "Priem nakladnykh v EGAIS",
        "Prosmotr ostatkov po pivu",
    ]
    
    action_items = [
        ("Net UKEP", "Ne smozhete podpisivat dokumenty"),
        ("Ne zagruzhen sertifikat JaCarta", "Risk shtrafa"),
    ]
    
    try:
        message = builder.build_reminder_message(
            client=client,
            deal_state=None,
            features=features,
            action_items=action_items,
            product_codes=["EGAIS", "MERCURY"],
        )
        
        print(f"[OK] Soobshchenie sformirovano")
        print(f"  Dlina: {len(message.text)} simvolov")
        print(f"  Funktsiy: {message.features_count}")
        print(f"  Prichin: {message.action_items_count}")
        
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def test_telegram_token():
    """Тест токена Telegram"""
    print("\n" + "="*70)
    print("ТЕСТ 3: TELEGRAM ТОКЕН")
    print("="*70)
    
    import aiohttp
    
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                
                if data.get('ok'):
                    bot = data.get('result')
                    print(f"[OK] Token rabochiy")
                    print(f"  Bot: @{bot.get('username')}")
                    print(f"  Name: {bot.get('first_name')}")
                    return True
                else:
                    print(f"[ERROR] Token ne rabochiy: {data}")
                    return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def main():
    """Запуск тестов"""
    print("\n")
    print("="*70)
    print(" " * 15 + "TEST SISTEMY ONBORDINGA" + " " * 15)
    print("="*70)
    
    results = {
        'config': test_config(),
        'message_builder': test_message_builder(),
        'telegram': await test_telegram_token(),
    }
    
    print("\n" + "="*70)
    print("ITOGI")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[WARN]"
        print(f"  {status} {test_name.upper()}")
    
    print(f"\nProydeno: {passed}/{total}")
    
    if passed == total:
        print("\n[OK] VSE TESTY PROYDENY!")
    else:
        print("\n[WARN] TREBUETSYA NASTROYKA!")
    
    print("="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
