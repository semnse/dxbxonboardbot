"""
Тест интеграции Bitrix24 -> Telegram с мок-данными
Симуляция получения данных из Bitrix и отправки сообщения
"""
import asyncio
import aiohttp
import os
import sys
from pathlib import Path
from dotenv import dotenv_values

# Загружаем .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings


# ============================================
# МОК-ДАННЫЕ (симуляция ответа Bitrix24)
# ============================================
MOCK_BITRIX_ITEM = {
    "ID": "999",
    "TITLE": 'ООО "Тестовая Торговая Точка"',
    "STAGE_ID": "DT1070_38:3150",
    "CATEGORY_ID": "38",
    "UF_CRM_20_1747732557645": "365611506",  # Telegram chat
    "UF_CRM_20_1763475932592": ["NO_UKEP", "NO_JACARTA"],  # Wait reasons
    "UF_CRM_20_1739184606910": ["8426", "8432"],  # Products: EGAIС, MERCURY
}

# Маппинг причин
REASON_NAMES = {
    'NO_UKEP': 'Нет УКЭП',
    'NO_JACARTA': 'Не загружен сертификат JaCarta',
    'NO_MERCURY_PLATFORM': 'Не подтверждена площадка в Меркурий',
    'NO_TRADE_HALL': 'Не заполнен торговый зал',
    'NO_NOMENKLATURA_MAPPING': 'Не проведено сопоставление номенклатуры',
    'NO_YZEDO_SUPPLIERS': 'Не подключены поставщики в ЮЗЭДО',
    'NO_GTIN_BINDING': 'Не привязан GTIN к номенклатуре',
    'NO_TRAINING_DATE': 'Не назначена дата обучения',
}

RISK_MESSAGES = {
    'NO_UKEP': 'Не сможете подписывать документы юридически значимой подписью',
    'NO_JACARTA': 'Не сможете отправлять документы в ЕГАИС — риск штрафа',
    'NO_MERCURY_PLATFORM': 'Не сможете гасить ВСД — задержки поставок',
    'NO_TRADE_HALL': 'Не сможете списывать алкоголь по кассе — только вручную',
    'NO_NOMENKLATURA_MAPPING': 'Ошибки в отчётности — система не поймёт товар',
    'NO_YZEDO_SUPPLIERS': 'Не сможете получать электронные накладные',
    'NO_GTIN_BINDING': 'Риск блокировки продаж маркированных товаров',
    'NO_TRAINING_DATE': 'Дольше будете разбираться с системой сами',
}

# Маппинг продуктов
PRODUCT_NAMES = {
    '8426': 'ЕГАИС',
    '8428': 'Накладные',
    '8430': 'ЮЗЭДО',
    '8432': 'Меркурий',
    '8434': 'Маркировка',
}

FEATURES_BY_PRODUCT = {
    'ЕГАИС': ['Приём накладных в ЕГАИС', 'Просмотр остатков по пиву'],
    'Меркурий': ['Гашение ВСД', 'Просмотр ветеринарных сертификатов'],
    'Маркировка': ['Приём маркированных товаров', 'Вывод из оборота'],
    'ЮЗЭДО': ['Получение электронных накладных', 'Подписание УКЭП'],
}


def extract_data(item):
    """Извлекает данные из элемента Bitrix"""
    # Telegram
    telegram_raw = item.get("UF_CRM_20_1747732557645", "")
    try:
        telegram_chat_id = int(telegram_raw) if telegram_raw else None
    except ValueError:
        telegram_chat_id = None
    
    # Причины ожидания
    wait_reasons = item.get("UF_CRM_20_1763475932592", [])
    if isinstance(wait_reasons, str):
        wait_reasons = [wait_reasons]
    
    # Продукты
    product_ids = item.get("UF_CRM_20_1739184606910", [])
    if isinstance(product_ids, str):
        product_ids = [product_ids]
    
    product_names = [PRODUCT_NAMES.get(pid, pid) for pid in product_ids]
    
    return {
        "id": item.get("ID"),
        "title": item.get("TITLE"),
        "telegram_chat_id": telegram_chat_id,
        "wait_reasons": wait_reasons,
        "products": product_names,
    }


def build_message(data):
    """Формирует сообщение для отправки"""
    lines = [
        f"🔍 <b>{data['title']}</b>, напоминаем о шагах для завершения внедрения",
        "",
        "✅ УЖЕ ДОСТУПНО:",
    ]
    
    for product in data['products']:
        features = FEATURES_BY_PRODUCT.get(product, [])
        for feature in features:
            lines.append(f"• {feature}")
    
    if not data['products']:
        lines.append("• Продукты не указаны")
    
    lines.append("")
    lines.append("⏳ ОСТАЛОСЬ СДЕЛАТЬ:")
    
    if data['wait_reasons']:
        for reason_code in data['wait_reasons']:
            reason_name = REASON_NAMES.get(reason_code, reason_code)
            risk = RISK_MESSAGES.get(reason_code, 'Риск не определён')
            lines.append(f"• {reason_name} → {risk}")
    else:
        lines.append("• Нет активных задач")
    
    lines.append("")
    lines.append("💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:")
    lines.append("Без этих шагов вы не сможете полноценно использовать систему.")
    lines.append("Это может привести к штрафам и проблемам с контролирующими органами.")
    lines.append("")
    lines.append("<i>Это тестовое сообщение от интеграции Bitrix24 → Telegram</i>")
    
    return "\n".join(lines)


async def send_telegram_message(chat_id: int, text: str):
    """Отправляет сообщение в Telegram"""
    token = settings.telegram_bot_token
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            data = await response.json()
            
            if response.status == 200 and data.get("ok"):
                msg_id = data.get('result', {}).get('message_id')
                return True, msg_id
            else:
                error = data.get('description', 'Unknown error')
                return False, error


async def main():
    print("="*70)
    print("ТЕСТ ИНТЕГРАЦИИ BITRIX24 -> TELEGRAM (МОК-ДАННЫЕ)")
    print("="*70)
    
    # Извлекаем данные из мок-элемента
    print("\n[1] ДАННЫЕ ИЗ BITRIX24 (симуляция):")
    data = extract_data(MOCK_BITRIX_ITEM)
    
    print(f"  ID: {data['id']}")
    print(f"  Название: {data['title']}")
    print(f"  Telegram Chat ID: {data['telegram_chat_id']}")
    print(f"  Причины ожидания: {data['wait_reasons']}")
    print(f"  Продукты: {data['products']}")
    
    # Формируем сообщение
    print("\n[2] ФОРМИРОВАНИЕ СООБЩЕНИЯ:")
    message = build_message(data)
    
    # Показываем превью
    plain_text = message.replace("<b>", "").replace("</b>", "") \
        .replace("<i>", "").replace("</i>", "")
    preview = plain_text[:300] + "..." if len(plain_text) > 300 else plain_text
    print(f"  Tekst soobshcheniya ({len(plain_text)} simvolov):")
    print("  " + "-"*60)
    for line in preview.split('\n')[:10]:
        print(f"  {line}")
    print("  " + "-"*60)
    
    # Отправляем
    print("\n[3] ОТПРАВКА В TELEGRAM:")
    chat_id = data['telegram_chat_id'] or 365611506
    
    success, result = await send_telegram_message(chat_id, message)
    
    if success:
        print(f"  [OK] Сообщение отправлено! (message_id={result})")
        print(f"  Проверьте Telegram чат {chat_id}")
    else:
        print(f"  [ERROR] Ошибка отправки: {result}")
    
    print("\n" + "="*70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("="*70)
    
    print("\n[INFO] Для реального теста:")
    print("  1. Откройте Bitrix24 -> Смарт-процессы -> Торговые точки")
    print("  2. Создайте новую точку со стадией 'Ждём действий клиента'")
    print("  3. Укажите Telegram чат: {}".format(chat_id))
    print("  4. Заполните причины ожидания и продукты")


if __name__ == "__main__":
    import sys
    asyncio.run(main())
