"""
Тест интеграции с Bitrix24
Получение торговых точек на стадии "Ждём действий клиента" и отправка сообщений
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.bitrix_smart_api import BitrixSmartProcessAPI
from app.config import settings


# ============================================
# КОНФИГУРАЦИЯ
# ============================================
import os
from pathlib import Path
from dotenv import dotenv_values

# Загружаем .env вручную ДО импорта settings
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

from app.config import settings

# Вставьте ваш webhook URL из Bitrix24
BITRIX_WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")

# ID стадии "Ждём действий клиента"
WAIT_STAGE_ID = "3150"

# ID воронки (категории)
CATEGORY_ID = "38"

# ID смарт-процесса "Торговые точки"
ENTITY_TYPE_ID = 1070


async def test_bitrix_connection():
    """Проверка подключения к Bitrix24"""
    print("="*70)
    print("ТЕСТ 1: ПОДКЛЮЧЕНИЕ К BITRIX24")
    print("="*70)
    
    if not BITRIX_WEBHOOK_URL:
        print("\n[ERROR] Bitrix webhook URL не настроен!")
        print("\n[INFO] Для настройки:")
        print("  1. Откройте Bitrix24")
        print("  2. Перейдите: Разработчикам -> Другое")
        print("  3. Создайте входящий webhook с правами:")
        print("     - CRM (чтение и запись)")
        print("     - Смарт-процессы (чтение и запись)")
        print("  4. Скопируйте URL в файл .env:")
        print("     BITRIX_WEBHOOK_URL=https://your-bitrix24.bitrix24.ru/rest/1/your_webhook/")
        return None
    
    print(f"\n[INFO] Webhook URL: {BITRIX_WEBHOOK_URL[:50]}...")
    
    api = BitrixSmartProcessAPI(
        webhook_url=BITRIX_WEBHOOK_URL,
        entity_type_id=ENTITY_TYPE_ID,
        category_id=CATEGORY_ID,
        target_stage_id=WAIT_STAGE_ID,
    )
    
    # Проверяем получение полей
    print("\n[INFO] Проверка подключения...")
    fields = await api.get_fields()
    
    if fields:
        print(f"[OK] Подключение успешно! Получено полей: {len(fields)}")
        return api
    else:
        print("[ERROR] Не удалось получить данные из Bitrix24")
        print("  Проверьте webhook URL и права доступа")
        return None


async def get_waiting_items(api: BitrixSmartProcessAPI):
    """Получение элементов на стадии ожидания"""
    print("\n" + "="*70)
    print("ТЕСТ 2: ТОРГОВЫЕ ТОЧКИ НА СТАДИИ 'ЖДЁМ ДЕЙСТВИЙ КЛИЕНТА'")
    print("="*70)
    
    print(f"\n[INFO] Получение элементов на стадии {WAIT_STAGE_ID}...")
    
    items = await api.get_waiting_items()
    
    print(f"\n[INFO] Найдено элементов: {len(items)}")
    
    if not items:
        print("\n[WARN] Нет торговых точек на этой стадии")
        print("  Добавьте тестовую точку в Bitrix24 и установите стадию 'Ждём действий клиента'")
        return []
    
    # Вывод информации по каждой точке
    for i, item in enumerate(items, 1):
        print(f"\n{'─'*70}")
        print(f"ТОЧКА #{i}")
        print(f"{'─'*70}")
        print(f"  ID: {item.get('ID')}")
        print(f"  Название: {item.get('TITLE')}")
        print(f"  Стадия: {item.get('STAGE_ID')}")
        
        # Извлекаем данные
        telegram_chat = api.extract_telegram_chat_id(item)
        wait_reasons = api.extract_wait_reasons(item)
        products = api.extract_product_codes(item)
        
        print(f"  Telegram chat ID: {telegram_chat or 'не указан'}")
        print(f"  Причины ожидания: {wait_reasons}")
        print(f"  Продукты: {products}")
    
    return items


async def send_test_messages(api: BitrixSmartProcessAPI, items: list, chat_id: int):
    """Отправка тестовых сообщений"""
    print("\n" + "="*70)
    print("ТЕСТ 3: ОТПРАВКА СООБЩЕНИЙ В TELEGRAM")
    print("="*70)
    
    if not items:
        print("\n[WARN] Нет элементов для отправки")
        return
    
    # Используем указанный chat_id для теста
    print(f"\n[INFO] Отправка тестового сообщения в чат {chat_id}...")
    
    import aiohttp
    
    # Формируем сообщение для первой точки
    item = items[0]
    company_name = api.extract_company_name(item)
    wait_reasons = api.extract_wait_reasons(item)
    products = api.extract_product_codes(item)
    
    # Маппинг причин
    reason_names = {
        'NO_UKEP': 'Нет УКЭП',
        'NO_JACARTA': 'Не загружен сертификат JaCarta',
        'NO_MERCURY_PLATFORM': 'Не подтверждена площадка в Меркурий',
        'NO_TRADE_HALL': 'Не заполнен торговый зал',
        'NO_NOMENKLATURA_MAPPING': 'Не проведено сопоставление номенклатуры',
        'NO_YZEDO_SUPPLIERS': 'Не подключены поставщики в ЮЗЭДО',
        'NO_GTIN_BINDING': 'Не привязан GTIN к номенклатуре',
        'NO_TRAINING_DATE': 'Не назначена дата обучения',
    }
    
    risk_messages = {
        'NO_UKEP': 'Не сможете подписывать документы юридически значимой подписью',
        'NO_JACARTA': 'Не сможете отправлять документы в ЕГАИС — риск штрафа',
        'NO_MERCURY_PLATFORM': 'Не сможете гасить ВСД — задержки поставок',
        'NO_TRADE_HALL': 'Не сможете списывать алкоголь по кассе — только вручную',
        'NO_NOMENKLATURA_MAPPING': 'Ошибки в отчётности — система не поймёт товар',
        'NO_YZEDO_SUPPLIERS': 'Не сможете получать электронные накладные',
        'NO_GTIN_BINDING': 'Риск блокировки продаж маркированных товаров',
        'NO_TRAINING_DATE': 'Дольше будете разбираться с системой сами',
    }
    
    # Формируем сообщение
    features = {
        'EGAIС': ['Приём накладных в ЕГАИС', 'Просмотр остатков по пиву'],
        'MERCURY': ['Гашение ВСД', 'Просмотр сертификатов'],
        'MARKING': ['Приём маркированных товаров', 'Вывод из оборота'],
        'YZEDO': ['Получение электронных накладных', 'Подписание УКЭП'],
    }
    
    message_lines = [
        f"🔍 <b>{company_name}</b>, напоминаем о шагах для завершения внедрения",
        "",
        "✅ УЖЕ ДОСТУПНО:",
    ]
    
    for prod in products:
        if prod in features:
            for feature in features[prod]:
                message_lines.append(f"• {feature}")
    
    if not products:
        message_lines.append("• Продукты не указаны")
    
    message_lines.append("")
    message_lines.append("⏳ ОСТАЛОСЬ СДЕЛАТЬ:")
    
    if wait_reasons:
        for reason_code in wait_reasons:
            reason_name = reason_names.get(reason_code, reason_code)
            risk = risk_messages.get(reason_code, 'Риск не определён')
            message_lines.append(f"• {reason_name} → {risk}")
    else:
        message_lines.append("• Нет активных задач")
    
    message_lines.append("")
    message_lines.append("💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:")
    message_lines.append("Без этих шагов вы не сможете полноценно использовать систему.")
    message_lines.append("")
    message_lines.append("<i>Это тестовое сообщение от интеграции Bitrix24 → Telegram</i>")
    
    message_text = "\n".join(message_lines)
    
    # Отправляем
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            
            if response.status == 200 and data.get("ok"):
                msg_id = data.get('result', {}).get('message_id')
                print(f"\n[OK] Сообщение отправлено! (message_id={msg_id})")
                print(f"\n[INFO] Текст сообщения:")
                print(f"{'─'*70}")
                # Выводим без HTML тегов для читаемости
                plain_text = message_text.replace("<b>", "").replace("</b>", "") \
                    .replace("<i>", "").replace("</i>", "")
                print(plain_text[:500] + "..." if len(plain_text) > 500 else plain_text)
                print(f"{'─'*70}")
                return True
            else:
                error = data.get('description', 'Unknown error')
                print(f"\n[ERROR] Ошибка отправки: {error}")
                return False


async def main():
    print("="*70)
    print("ТЕСТ ИНТЕГРАЦИИ BITRIX24 -> TELEGRAM")
    print("="*70)
    
    # Тест 1: Подключение
    api = await test_bitrix_connection()
    
    if not api:
        print("\n[ERROR] Тест не пройден. Настройте Bitrix24 webhook.")
        return
    
    # Тест 2: Получение элементов
    items = await get_waiting_items(api)
    
    # Тест 3: Отправка сообщений
    print(f"\n[INFO] Для теста введите ваш Chat ID (или нажмите Enter для пропуска):")
    chat_id_input = input("Chat ID: ").strip()
    
    if chat_id_input:
        try:
            chat_id = int(chat_id_input)
            await send_test_messages(api, items, chat_id)
        except ValueError:
            print("[ERROR] Неверный формат Chat ID")
    else:
        print("[INFO] Пропуск отправки сообщений")
    
    print("\n" + "="*70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
