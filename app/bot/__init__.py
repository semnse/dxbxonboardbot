"""
Bot module
"""
from aiogram import Dispatcher, Bot

from app.config import settings
from app.bot.scheduler import start_scheduler, shutdown_scheduler

# Глобальные bot и dp (создаются один раз)
bot = Bot(token=settings.telegram_bot_token)
dp = Dispatcher()

__all__ = [
    "bot",
    "dp",
    "start_scheduler",
    "shutdown_scheduler",
]
