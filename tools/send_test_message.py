"""
Скрипт отправки тестового сообщения в Telegram
"""
import asyncio
import aiohttp
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


async def send_test_message(chat_id: int, message_text: str):
    """Отправляет тестовое сообщение в Telegram"""
    
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    print(f"🔍 Отправка сообщения в чат {chat_id}...")
    print(f"📝 Токен: {token[:20]}...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            
            if response.status == 200 and data.get("ok"):
                message_id = data.get("result", {}).get("message_id")
                print(f"✅ Сообщение отправлено успешно! (message_id={message_id})")
                return True
            else:
                error_desc = data.get("description", "Unknown error")
                error_code = data.get("error_code")
                print(f"❌ Ошибка: {error_code} - {error_desc}")
                return False


async def get_bot_info():
    """Получает информацию о боте"""
    
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            
            if data.get("ok"):
                result = data.get("result", {})
                print(f"🤖 Бот: @{result.get('username')} (id={result.get('id')})")
                print(f"   Имя: {result.get('first_name')}")
                return result
            else:
                print(f"❌ Ошибка получения информации о боте: {data.get('description')}")
                return None


async def get_chat_info(chat_id: int):
    """Получает информацию о чате"""
    
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/getChat"
    
    payload = {"chat_id": chat_id}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            
            if data.get("ok"):
                result = data.get("result", {})
                print(f"💬 Чат: {result.get('title') or result.get('first_name') or 'N/A'}")
                print(f"   Type: {result.get('type')}")
                print(f"   ID: {result.get('id')}")
                return result
            else:
                print(f"❌ Ошибка получения информации о чате: {data.get('description')}")
                return None


async def main():
    print("="*70)
    print("ТЕСТ ОТПРАВКИ СООБЩЕНИЯ TELEGRAM")
    print("="*70)
    
    # Получаем информацию о боте
    print("\n1️⃣ Информация о боте:")
    bot_info = await get_bot_info()
    
    if not bot_info:
        print("\n❌ Не удалось получить информацию о боте. Проверьте токен.")
        return
    
    # Запрашиваем chat_id у пользователя
    print("\n2️⃣ Введите chat_id для отправки тестового сообщения:")
    print("   (Чтобы узнать chat_id, напишите боту @userinfobot или @getmyid_bot)")
    
    chat_id_input = input("\nChat ID: ").strip()
    
    if not chat_id_input:
        print("❌ Chat ID не указан")
        return
    
    try:
        chat_id = int(chat_id_input)
    except ValueError:
        print(f"❌ Неверный формат chat_id: {chat_id_input}")
        return
    
    # Получаем информацию о чате
    print("\n3️⃣ Информация о чате:")
    await get_chat_info(chat_id)
    
    # Формируем тестовое сообщение
    test_message = """
🔍 <b>Тестовое сообщение от бота онбординга</b>

✅ УЖЕ ДОСТУПНО:
• Приём алкогольных накладных в ЕГАИС
• Просмотр остатков по пиву

⏳ ОСТАЛОСЬ СДЕЛАТЬ:
• Нет УКЭП → Не сможете подписывать документы юридически значимой подписью
• Не загружен сертификат JaCarta → Не сможете отправлять документы в ЕГАИС

💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:
Без этих шагов вы не сможете легально работать с алкоголем. Это может привести к штрафам от контролирующих органов.

---
Это тестовое сообщение. Если вы его видите — бот работает! ✅
"""
    
    # Отправляем сообщение
    print("\n4️⃣ Отправка сообщения:")
    success = await send_test_message(chat_id, test_message)
    
    print("\n" + "="*70)
    if success:
        print("✅ ТЕСТ ПРОЙДЕН! Бот работает корректно.")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН! Проверьте токен и chat_id.")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
