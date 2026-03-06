"""
Тест отправки отчёта в топики

Запускается вручную для проверки что отчёты приходят в правильные топики
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database.connection import get_session_maker
from app.database.models import ChatBinding
from sqlalchemy import select


async def test_send_to_topics():
    """Тест отправки отчёта в топики"""
    
    print("\n" + "="*60)
    print("ТЕСТ: Отправка отчёта в топики")
    print("="*60)
    
    from aiogram import Bot
    
    bot = Bot(token=settings.telegram_bot_token)
    session_maker = get_session_maker()
    
    try:
        # Получаем все активные привязки с message_thread_id
        async with session_maker() as session:
            result = await session.execute(
                select(ChatBinding).where(
                    ChatBinding.is_active == True,
                    ChatBinding.message_thread_id != None,
                    ChatBinding.message_thread_id > 0
                )
            )
            chat_bindings = result.scalars().all()
        
        print(f"\n📊 Найдено {len(chat_bindings)} привязок с топиками:")
        for binding in chat_bindings:
            print(f"  • {binding.company_name}: chat={binding.chat_id}, thread={binding.message_thread_id}")
        
        if not chat_bindings:
            print("\n⚠️ Нет привязок с топиками!")
            return False
        
        # Отправляем тестовое сообщение в каждый топик
        print("\n🚀 Отправка тестовых сообщений...")
        
        for binding in chat_bindings:
            try:
                message_text = f"""🧪 ТЕСТОВОЕ СООБЩЕНИЕ

📋 Компания: {binding.company_name}
🔗 Bitrix ID: {binding.bitrix_deal_id}
💬 Chat ID: {binding.chat_id}
📌 Thread ID: {binding.message_thread_id}

✅ Если вы видите это в правильном топике - всё работает!"""
                
                await bot.send_message(
                    chat_id=binding.chat_id,
                    text=message_text,
                    parse_mode="Markdown",
                    message_thread_id=binding.message_thread_id,
                    disable_notification=False,
                )
                
                print(f"  ✅ Отправлено в топик {binding.message_thread_id} ({binding.company_name})")
                
            except Exception as e:
                print(f"  ❌ Ошибка отправки в {binding.company_name}: {e}")
        
        print("\n" + "="*60)
        print("✅ ТЕСТ ЗАВЕРШЁН")
        print("="*60)
        print("\n📋 Проверьте Telegram:")
        print("  • Откройте чат с топиками")
        print("  • Проверьте что сообщения пришли в правильные топики")
        print("  • Если всё ок - бот работает корректно")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await bot.session.close()


if __name__ == "__main__":
    result = asyncio.run(test_send_to_topics())
    exit(0 if result else 1)
