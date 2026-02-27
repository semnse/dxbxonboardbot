"""Проверка конфигурации в приложении"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Проверяем, читается ли .env
from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))

print("="*70)
print("ПРОВЕРКА .ENV")
print("="*70)
print(f"BITRIX_WEBHOOK_URL: {env_values.get('BITRIX_WEBHOOK_URL', 'NOT SET')[:50]}...")
print(f"TELEGRAM_BOT_TOKEN: {env_values.get('TELEGRAM_BOT_TOKEN', 'NOT SET')[:20]}...")

# Теперь проверяем settings
from app.config import settings

print("\n" + "="*70)
print("ПРОВЕРКА SETTINGS")
print("="*70)
print(f"BITRIX_WEBHOOK_URL: {settings.bitrix_webhook_url[:50] if settings.bitrix_webhook_url else 'None'}...")
print(f"TELEGRAM_BOT_TOKEN: {settings.telegram_bot_token[:20] if settings.telegram_bot_token else 'None'}...")

# Проверяем BitrixPollingService
from app.services.bitrix_polling_service import BitrixPollingService

bitrix = BitrixPollingService()
print("\n" + "="*70)
print("ПРОВЕРКА BitrixPollingService")
print("="*70)
print(f"webhook_url: {bitrix.webhook_url[:50] if bitrix.webhook_url else 'None'}...")
