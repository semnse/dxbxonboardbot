"""Прямой тест get_item_by_id"""
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

from app.services.bitrix_polling_service import BitrixPollingService


async def main():
    print("="*70)
    print("TEST: get_item_by_id(6784)")
    print("="*70)
    
    bitrix = BitrixPollingService()
    
    print("\nZapusk get_item_by_id...")
    result = await bitrix.get_item_by_id(6784)
    
    print(f"Result: {result}")
    
    if result:
        print(f"\n[OK] KARTOCHKA NAIDENA!")
        print(f"  ID: {result.get('id')}")
        print(f"  Title: {result.get('title', '')[:80]}")
        print(f"  Stage: {result.get('stageId')}")
        print(f"  Telegram: {result.get('ufCrm20_1747732557645')}")
    else:
        print(f"\n[ERROR] KARTOCHKA NE NAIDENA!")


if __name__ == "__main__":
    asyncio.run(main())
