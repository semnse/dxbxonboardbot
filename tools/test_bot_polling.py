"""Тест polling бота"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

bot = Bot(token=os.environ.get('TELEGRAM_BOT_TOKEN', ''))
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    print(f"[HANDLER] /start from {message.from_user.first_name} (chat={message.chat.id})")
    await message.answer("✅ Бот работает! Polling обрабатывает сообщения.")


@dp.message(Command("add"))
async def cmd_add(message: Message):
    print(f"[HANDLER] /add from {message.from_user.first_name} (chat={message.chat.id})")
    await message.answer(f"✅ Команда /add получена! Аргументы: {message.text}")


async def main():
    print("="*70)
    print("ЗАПУСК POLLING ТЕСТА")
    print("="*70)
    print(f"Бот: @{(await bot.get_me()).username}")
    print("\nОжидание сообщений... (нажмите Ctrl+C для остановки)")
    print("="*70)
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nОстановлено")
