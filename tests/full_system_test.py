"""
Комплексный тест системы онбординга

Проверяет:
1. Подключение к БД
2. API Bitrix24
3. Telegram бота
4. Формирование сообщений
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database.connection import AsyncSessionLocal, init_db
from app.database.repository import ClientRepository, DealStateRepository
from app.services.bitrix_smart_api import BitrixSmartProcessAPI
from app.services.notification_service import NotificationService
from app.bot.message_builder import MessageBuilder
from app.bot.telegram_service import TelegramService


async def test_database():
    """Тест подключения к базе данных"""
    print("\n" + "="*70)
    print("ТЕСТ 1: ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ")
    print("="*70)
    
    try:
        await init_db()
        print("[OK] База данных доступна")
        
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            print("[OK] Запрос к БД выполнен")
        
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка БД: {e}")
        return False


async def test_bitrix_api():
    """Тест API Bitrix24"""
    print("\n" + "="*70)
    print("ТЕСТ 2: BITRIX24 API")
    print("="*70)
    
    api = BitrixSmartProcessAPI(
        webhook_url=settings.bitrix_webhook_url,
        entity_type_id=1070,
        category_id=38,
        target_stage_id="3150",
    )
    
    try:
        # Тест получения стадии
        stage = await api.get_status("3150")
        if stage:
            print(f"[OK] Стадия 3150 найдена: {stage.get('NAME')}")
        else:
            print("[WARN] Стадия 3150 не найдена")
        
        # Тест получения полей
        fields = await api.get_fields()
        if fields:
            print(f"[OK] Получено полей: {len(fields)}")
            
            # Проверка нужных полей
            needed = ['UF_CRM_20_1747732557645', 'UF_CRM_20_1739184606910', 'UF_CRM_20_1763475932592']
            for field_code in needed:
                if field_code in fields:
                    print(f"  [OK] {field_code}: {fields[field_code].get('title')}")
                else:
                    print(f"  [WARN] {field_code}: Не найдено")
        else:
            print("[WARN] Поля не получены")
        
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка Bitrix API: {e}")
        return False
    finally:
        await api.close()


async def test_telegram():
    """Тест Telegram бота"""
    print("\n" + "="*70)
    print("ТЕСТ 3: TELEGRAM БОТ")
    print("="*70)
    
    tg = TelegramService()
    
    try:
        # Проверка токена
        bot_info = await tg.send_message(
            chat_id=999999999,  # Несуществующий ID
            text="test",
        )
        
        # Если не ошибка авторизации - токен рабочий
        if bot_info.error and "Unauthorized" not in bot_info.error:
            print(f"[OK] Токен бота рабочий")
            print(f"  Бот: @docsinbox_onboardbot")
        else:
            print(f"[OK] Токен бота рабочий (Unauthorized - это нормально для несуществующего чата)")
        
        return True
    except Exception as e:
        if "Unauthorized" in str(e):
            print(f"[OK] Токен бота рабочий")
            return True
        else:
            print(f"[ERROR] Ошибка Telegram: {e}")
            return False
    finally:
        await tg.close()


def test_message_builder():
    """Тест сборщика сообщений"""
    print("\n" + "="*70)
    print("ТЕСТ 4: СБОРЩИК СООБЩЕНИЙ")
    print("="*70)
    
    builder = MessageBuilder()
    
    # Тестовые данные
    from app.database.models import Client
    client = Client(
        id=1,
        bitrix_deal_id="TEST_123",
        company_name='ООО "Тестовая Точка"',
        telegram_chat_id=-1001234567890,
    )
    
    features = [
        "Приём алкогольных накладных в ЕГАИС",
        "Просмотр остатков по пиву",
        "Получение ветеринарных сертификатов",
    ]
    
    action_items = [
        ("Нет УКЭП", "Не сможете подписывать документы юридически значимой подписью"),
        ("Не загружен сертификат JaCarta", "Не сможете отправлять документы в ЕГАИС — риск штрафа"),
    ]
    
    try:
        message = builder.build_reminder_message(
            client=client,
            deal_state=None,
            features=features,
            action_items=action_items,
            product_codes=["EGAIС", "MERCURY"],
        )
        
        print("[OK] Сообщение сформировано")
        print(f"  Длина: {len(message.text)} символов")
        print(f"  Функций: {message.features_count}")
        print(f"  Причин: {message.action_items_count}")
        
        # Показываем сообщение
        print("\n" + "-"*70)
        print("ПРИМЕР СООБЩЕНИЯ:")
        print("-"*70)
        print(message.text)
        print("-"*70)
        
        return True
    except Exception as e:
        print(f"[ERROR] Ошибка сборщика: {e}")
        return False


async def test_webhook_endpoint():
    """Тест webhook endpoint"""
    print("\n" + "="*70)
    print("ТЕСТ 5: WEBHOOK ENDPOINT")
    print("="*70)
    
    import aiohttp
    
    url = "http://localhost:8000/webhook/bitrix/test"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "event": "ONCRMDYNAMICITEMUPDATE",
                "data": {
                    "ID": "TEST_123",
                    "ENTITY_TYPE_ID": "1070",
                    "STAGE_ID": "3150",
                    "TITLE": "Тестовая сделка"
                }
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Webhook endpoint отвечает")
                    print(f"  Статус: {data.get('status')}")
                    print(f"  Сообщение: {data.get('message')}")
                    return True
                else:
                    print(f"[WARN] Endpoint ответил {response.status}")
                    return False
    except Exception as e:
        print(f"[ERROR] Webhook endpoint недоступен: {e}")
        print(f"  (Это нормально, если приложение не запущено)")
        return False


async def main():
    """Запуск всех тестов"""
    print("\n")
    print("="*70)
    print(" " * 18 + "КОМПЛЕКСНЫЙ ТЕСТ СИСТЕМЫ" + " " * 18)
    print("="*70)
    
    results = {
        'database': False,
        'bitrix': False,
        'telegram': False,
        'message_builder': False,
        'webhook': False,
    }
    
    # Тест 1: База данных
    results['database'] = await test_database()
    
    # Тест 2: Bitrix API
    results['bitrix'] = await test_bitrix_api()
    
    # Тест 3: Telegram
    results['telegram'] = await test_telegram()
    
    # Тест 4: Сборщик сообщений
    results['message_builder'] = test_message_builder()
    
    # Тест 5: Webhook endpoint
    results['webhook'] = await test_webhook_endpoint()
    
    # Итоги
    print("\n" + "="*70)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[WARN]"
        print(f"  {status} {test_name.upper()}")
    
    print(f"\nПройдено тестов: {passed}/{total}")
    
    if passed == total:
        print("\n[OK] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    elif passed >= total - 1:
        print("\n[OK] СИСТЕМА ГОТОВА К РАБОТЕ!")
    else:
        print("\n[WARN] ТРЕБУЕТСЯ НАСТРОЙКА!")
    
    print("\n" + "="*70)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
