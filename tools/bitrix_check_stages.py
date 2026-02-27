"""Проверка стадий в Bitrix24"""
import asyncio
import aiohttp
import os
import sys
import json
from pathlib import Path
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).parent.parent))

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")


async def main():
    print("="*70)
    print("BITRIX24: ПРОВЕРКА СТАДИЙ И ЭЛЕМЕНТОВ")
    print("="*70)
    
    # 1. Получаем все элементы без фильтра - смотрим какие стадии есть
    print("\n[1] Получаем первые 50 элементов (любые стадии)...")
    
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    params = {
        "entityTypeId": 1070,
        "select": ["ID", "TITLE", "STAGE_ID", "CATEGORY_ID"],
        "limit": 50
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params) as response:
            data = await response.json()
            
            if data.get('result'):
                items = data['result'].get('items', [])
                print(f"  Найдено элементов: {len(items)}")
                
                # Считаем стадии
                stage_counts = {}
                for item in items:
                    stage = item.get('STAGE_ID', 'UNKNOWN')
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1
                
                print("\n  Распределение по стадиям:")
                for stage, count in sorted(stage_counts.items(), key=lambda x: -x[1]):
                    print(f"    {stage}: {count} шт.")
                
                # Показываем примеры элементов на разных стадиях
                print("\n  Примеры элементов:")
                for item in items[:5]:
                    print(f"    ID={item.get('ID')}, Stage={item.get('STAGE_ID')}, Title={item.get('TITLE', '')[:40]}")
    
    # 2. Пробуем найти элементы со стадией содержащей "3150"
    print("\n[2] Ищем элементы со стадией содержащей '3150'...")
    
    # В Bitrix24 смарт-процессы используют формат DT{type}_{category}:{stage}
    # Для наших параметров: DT1070_38:3150
    # Но также может быть просто числовой ID
    
    test_stages = [
        "3150",
        "DT1070_38:3150", 
        "DT1070:3150",
        ":3150",
    ]
    
    for stage_filter in test_stages:
        print(f"\n  Пробуем фильтр STAGE_ID={stage_filter}...")
        
        params = {
            "entityTypeId": 1070,
            "filter": {"STAGE_ID": stage_filter},
            "select": ["ID", "TITLE", "STAGE_ID"],
            "limit": 5
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if data.get('result'):
                    items = data['result'].get('items', [])
                    if items:
                        print(f"    [OK] Найдено: {len(items)}")
                        for item in items[:2]:
                            print(f"      ID={item.get('ID')}, Stage={item.get('STAGE_ID')}")
                    else:
                        print(f"    [EMPTY] Нет элементов")
                else:
                    print(f"    [ERROR] {data}")
    
    # 3. Получаем список всех доступных стадий
    print("\n[3] Получаем список стадий из CRM...")
    
    # Для смарт-процессов нужно использовать другой метод
    status_url = f"{WEBHOOK_URL}/crm.status.list.json"
    params = {
        "entityTypeId": 1070,
        "categoryId": 38
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(status_url, json=params) as response:
            data = await response.json()
            
            if data.get('result'):
                statuses = data['result']
                print(f"  Найдено стадий: {len(statuses)}")
                for s in statuses:
                    stage_id = s.get('STATUS_ID', s.get('ID', 'N/A'))
                    name = s.get('NAME', 'N/A')
                    print(f"    {stage_id}: {name}")
            else:
                print(f"  [ERROR] {data}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
