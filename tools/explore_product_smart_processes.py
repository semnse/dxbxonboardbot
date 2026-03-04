"""
Тест: Изучение структуры смарт-процессов продуктов

Задача:
1. Получить основную карточку (смарт-процесс 1070)
2. Найти связанные смарт-процессы продуктов
3. Получить стадии воронок каждого продукта
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
import aiohttp


async def explore_smart_processes():
    """Изучение структуры смарт-процессов"""
    
    print("\n" + "="*60)
    print("ИЗУЧЕНИЕ СТРУКТУРЫ СМАРТ-ПРОЦЕССОВ ПРОДУКТОВ")
    print("="*60)
    
    webhook_url = settings.bitrix_webhook_url
    print(f"\nWebhook: {webhook_url[:50]}...")
    
    # Основная карточка (Торговые точки)
    ENTITY_TYPE_ID = 1070
    
    async with aiohttp.ClientSession() as session:
        # ===== ТЕСТ 1: Получаем карточку с UF-полями =====
        print("\n[1] Получение карточки с UF-полями продуктов...")
        
        # Возьмём карточку из логов: ID=18306
        test_card_id = 18306
        
        async with session.post(
            f"{webhook_url}/crm.item.get.json",
            json={
                "entityTypeId": ENTITY_TYPE_ID,
                "id": test_card_id
            }
        ) as response:
            result = await response.json()
            item = result.get('result', {})
            
            if item:
                print(f"  ✅ Карточка найдена: {item.get('title', '')[:50]}")
                print(f"  ID: {item.get('id')}")
                print(f"  Стадия: {item.get('stageId')}")
                
                # Показываем все UF-поля
                print(f"\n  📋 UF-поля:")
                for key, value in item.items():
                    if key.lower().startswith('uf'):
                        if isinstance(value, str) and len(value) > 100:
                            value = value[:100] + "..."
                        print(f"    {key}: {value}")
            else:
                print(f"  ❌ Карточка не найдена: {result}")
        
        # ===== ТЕСТ 2: Ищем связанные смарт-процессы =====
        print("\n[2] Поиск связанных смарт-процессов...")
        
        # Пробуем получить список всех смарт-процессов компании
        async with session.post(
            f"{webhook_url}/crm.type.list.json",
            json={}
        ) as response:
            result = await response.json()
            types = result.get('result', [])
            
            if types:
                print(f"  ✅ Найдено смарт-процессов: {len(types)}")
                for t in types[:10]:  # Показываем первые 10
                    print(f"    - ID: {t.get('ID')}, NAME: {t.get('NAME')}")
            else:
                print(f"  ⚠️ Не найдено: {result}")
        
        # ===== ТЕСТ 3: Проверяем конкретные смарт-процессы продуктов =====
        print("\n[3] Проверка смарт-процессов продуктов...")
        
        # Предполагаемые ID смарт-процессов продуктов
        # (нужно уточнить в Bitrix24)
        product_entities = [
            {"id": "1071", "name": "ЕГАИС"},
            {"id": "1072", "name": "Меркурий"},
            {"id": "1073", "name": "Маркировка"},
            {"id": "1074", "name": "Накладные"},
            {"id": "1075", "name": "ЮЗЭДО"},
        ]
        
        for product in product_entities:
            async with session.post(
                f"{webhook_url}/crm.item.list.json",
                json={
                    "entityTypeId": product["id"],
                    "filter": {"PARENT_ID": test_card_id},  # Ищем связанные с основной карточкой
                    "select": ["id", "title", "stageId"],
                    "limit": 5
                }
            ) as response:
                result = await response.json()
                items = result.get('result', {}).get('items', [])
                
                if items:
                    print(f"  ✅ {product['name']} (ID={product['id']}): {len(items)} записей")
                    for item in items[:2]:
                        print(f"    - ID={item.get('id')}, Stage={item.get('stageId')}, Title={item.get('title', '')[:40]}")
                else:
                    print(f"  ⚠️ {product['name']}: нет записей")
        
        # ===== ТЕСТ 4: Получаем стадии воронок =====
        print("\n[4] Получение стадий воронок продуктов...")
        
        # Для примера - стадии для ЕГАИС
        async with session.post(
            f"{webhook_url}/crm.status.list.json",
            json={
                "entityTypeId": 1071,  # ЕГАИС
                "type": "STATUS"
            }
        ) as response:
            result = await response.json()
            stages = result.get('result', [])
            
            if stages:
                print(f"  ✅ Стадии для ЕГАИС: {len(stages)}")
                for stage in stages[:10]:
                    print(f"    - {stage.get('STATUS_ID')}: {stage.get('NAME')}")
            else:
                print(f"  ⚠️ Не найдено: {result}")
    
    print("\n" + "="*60)
    print("ИЗУЧЕНИЕ ЗАВЕРШЕНО")
    print("="*60)
    print("\n📋 Следующие шаги:")
    print("  1. Узнать точные ID смарт-процессов продуктов в Bitrix24")
    print("  2. Узнать ID воронок для каждого продукта")
    print("  3. Настроить маппинг стадий → тексты для пользователя")


if __name__ == "__main__":
    asyncio.run(explore_smart_processes())
