"""
Bot module
"""
from app.bot.scheduler import start_scheduler, shutdown_scheduler
from app.bot.commands import bot, dp

__all__ = [
    "start_scheduler",
    "shutdown_scheduler",
    "bot",
    "dp",
]
