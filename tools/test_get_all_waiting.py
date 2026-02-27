"""Тест получения всех карточек со стадиями ожидания"""
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

from app.services.bitrix_polling_service import BitrixPollingService


async def main():
    print("="*70)
    print("TEST: Poluchenie vsekh kartochek so stadiy ozhidaniya")
    print("="*70)
    
    bitrix = BitrixPollingService()
    
    print("\n[1] Zapuskaem get_waiting_items(limit=700)...")
    items = await bitrix.get_waiting_items(limit=700)
    
    print(f"\n[2] NAIDENO: {len(items)} kartochek")
    
    # Gruppiruem po stadiyam
    by_stage = {}
    for item in items:
        stage = item.get('stageId', 'UNKNOWN')
        if stage not in by_stage:
            by_stage[stage] = 0
        by_stage[stage] += 1
    
    print("\n[3] RAZBIVKA PO STADIYAM:")
    for stage, count in sorted(by_stage.items(), key=lambda x: -x[1]):
        print(f"    {stage}: {count} kartochek")
    
    # Pokazyvaem pervye 10
    print("\n[4] PERVYE 10 KARTOCHEK:")
    for item in items[:10]:
        stage = item.get('stageId', '')
        title = item.get('title', '')[:50]
        print(f"    ID={item.get('id')}: {title}")
        print(f"      Stage: {stage}")
    
    if len(items) > 10:
        print(f"    ... i eshche {len(items) - 10}")
    
    print("\n" + "="*70)
    print("TEST ZAVRESHEN")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
