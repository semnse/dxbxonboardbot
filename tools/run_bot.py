"""
Запуск бота отдельно от FastAPI
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем .env
from dotenv import load_dotenv
load_dotenv()

from app.bot.commands import dp, bot


async def main():
    """Запуск бота"""
    logger.info("Starting bot polling...")
    logger.info(f"Bot: @{(await bot.get_me()).username}")
    
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
