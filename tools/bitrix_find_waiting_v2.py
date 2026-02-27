"""Поиск элементов на стадии 'Ждём действий клиента'"""
import asyncio
import aiohttp
import os
import sys
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
    print("BITRIX24: ПОИСК ЭЛЕМЕНТОВ 'ЖДЁМ ДЕЙСТВИЙ КЛИЕНТА'")
    print("="*70)
    
    # Стадии "Ждём действий клиента" из списка
    wait_stages = [
        "DT1070_38:UC_ILDKHV",  # Ждём действий клиента
        "DT1070_38:UC_70SK2H",  # Чек работы системы
        "DT1070_38:UC_B7P2X4",  # Выведена на MRR
        "DT1070_38:UC_JK4IJR",  # Подключение поставщиков
        "DT1070_38:UC_NZK4JJ",  # Подключение поставщиков
        "DT1070_38:UC_XRWEHG",  # Чек работы системы
        "DT1070_38:UC_9JH4GA",  # Не можем завершить
        "DT1070_38:UC_REJAS2",  # Завершение внедрения
        "DT1070_38:3",          # Не можем завершить
    ]
    
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    total_found = 0
    
    for stage_id in wait_stages[:5]:  # Проверяем первые 5
        print(f"\n[INFO] Проверка стадии: {stage_id}...")
        
        params = {
            "entityTypeId": 1070,
            "filter": {"STAGE_ID": stage_id},
            "select": [
                "ID", "TITLE", "STAGE_ID",
                "UF_CRM_20_1747732557645",  # telegram
                "UF_CRM_20_1763475932592",  # wait_reasons
                "UF_CRM_20_1739184606910",  # products
            ],
            "limit": 10
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                
                if data.get('result'):
                    items = data['result'].get('items', [])
                    if items:
                        print(f"  [OK] Найдено: {len(items)}")
                        total_found += len(items)
                        
                        # Показываем первый элемент
                        item = items[0]
                        print(f"\n  Пример элемента:")
                        print(f"    ID: {item.get('ID')}")
                        print(f"    Название: {item.get('TITLE', '')[:60]}")
                        print(f"    Стадия: {item.get('STAGE_ID')}")
                        
                        # Проверяем поля
                        telegram = item.get('UF_CRM_20_1747732557645', 'не указан')
                        reasons = item.get('UF_CRM_20_1763475932592', [])
                        products = item.get('UF_CRM_20_1739184606910', [])
                        
                        print(f"    Telegram: {telegram}")
                        print(f"    Причины: {reasons}")
                        print(f"    Продукты: {products}")
                    else:
                        print(f"  [EMPTY] Нет элементов")
                else:
                    print(f"  [ERROR] {data}")
    
    print(f"\n{'='*70}")
    print(f"ВСЕГО НАЙДЕНО: {total_found} элементов")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
