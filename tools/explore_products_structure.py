"""
Скрипт для изучения структуры продуктов в Bitrix24

Задача:
1. Получить основную карточку
2. Найти все связанные карточки продуктов
3. Узнать их стадии и воронки
4. Сохранить структуру для настройки маппинга
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
import aiohttp


async def explore_products_structure():
    """Изучение структуры продуктов"""
    
    print("\n" + "="*60)
    print("ИЗУЧЕНИЕ СТРУКТУРЫ ПРОДУКТОВ")
    print("="*60)
    
    webhook_url = settings.bitrix_webhook_url
    
    # Тестовая карточка из логов
    test_card_id = 18306
    
    async with aiohttp.ClientSession() as session:
        # ===== 1. Получаем основную карточку =====
        print("\n[1] Получение основной карточки...")
        
        async with session.post(
            f"{webhook_url}/crm.item.get.json",
            json={
                "entityTypeId": 1070,  # Торговые точки
                "id": test_card_id
            }
        ) as response:
            result = await response.json()
            main_item = result.get('result', {})
            
            if main_item:
                print(f"  ✅ Карточка: {main_item.get('title', '')[:60]}")
                print(f"  Стадия: {main_item.get('stageId')}")
                
                # Ищем UF-поля связанные с продуктами
                print(f"\n  📋 UF-поля:")
                product_fields = {}
                for key, value in main_item.items():
                    if key.lower().startswith('uf'):
                        if value:
                            product_fields[key] = value
                            print(f"    {key}: {str(value)[:100]}")
                
                # Сохраняем для анализа
                print(f"\n  💾 Найдено UF-полей: {len(product_fields)}")
            else:
                print(f"  ❌ Карточка не найдена")
                return
        
        # ===== 2. Пробуем найти связанные элементы =====
        print("\n[2] Поиск связанных элементов...")
        
        # Поле связи может называться по-разному, пробуем варианты
        bind_fields = [
            'UF_CRM_1234567890',  # Пример
            'PRODUCTS',
            'UF_PRODUCTS',
        ]
        
        for field in bind_fields:
            value = main_item.get(field)
            if value:
                print(f"  💡 Поле {field}: {value}")
        
        # ===== 3. Получаем список всех смарт-процессов =====
        print("\n[3] Получение списка смарт-процессов...")
        
        # К сожалению, crm.type.list может быть недоступен
        # Попробуем получить стадии для разных entityTypeId
        
        # Пример: пробуем несколько ID
        test_entity_ids = [
            (1070, "Торговые точки"),
            (1071, "Продукт 1"),
            (1072, "Продукт 2"),
            (1073, "Продукт 3"),
            (1074, "Продукт 4"),
            (1075, "Продукт 5"),
        ]
        
        for entity_id, entity_name in test_entity_ids:
            async with session.post(
                f"{webhook_url}/crm.status.list.json",
                json={
                    "entityTypeId": entity_id,
                    "type": "STATUS"
                }
            ) as response:
                result = await response.json()
                stages = result.get('result', [])
                
                if stages:
                    print(f"  ✅ {entity_name} (ID={entity_id}): {len(stages)} стадий")
                    
                    # Показываем первые 5 стадий
                    for stage in stages[:5]:
                        print(f"    - {stage.get('STATUS_ID')}: {stage.get('NAME')}")
                else:
                    print(f"  ⚠️ {entity_name}: нет стадий")
        
        # ===== 4. Сохраняем результат =====
        print("\n[4] Сохранение результатов...")
        
        output = {
            'main_card': {
                'id': main_item.get('id'),
                'title': main_item.get('title'),
                'stageId': main_item.get('stageId'),
                'uf_fields': {
                    k: str(v)[:200] for k, v in product_fields.items()
                },
            },
            'next_steps': [
                "1. Узнать точные ID смарт-процессов продуктов в Bitrix24",
                "2. Узнать названия полей связи (UF-поля)",
                "3. Получить тексты сообщений для каждой стадии",
            ]
        }
        
        output_file = 'tools/product_structure.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ Результаты сохранены в {output_file}")
    
    print("\n" + "="*60)
    print("ИЗУЧЕНИЕ ЗАВЕРШЕНО")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(explore_products_structure())
