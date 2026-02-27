"""
Финальный тест интеграции Bitrix24 -> Telegram
Демонстрация полной логики работы с мок-данными
"""
import asyncio
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

from app.config import settings
import aiohttp


# Мок-данные (симуляция того, что придет из Bitrix24)
MOCK_BITRIX_ITEMS = [
    {
        'id': 5304,
        'title': 'ООО "Билик" 9707032028',
        'stageId': 'DT1070_38:UC_70SK2H',
        'uf_crm_20_1747732557645': 365611506,  # Ваш Telegram ID
        'uf_crm_20_1763475932592': ['NO_UKEP', 'NO_JACARTA'],
        'uf_crm_20_1739184606910': ['8426', '8432'],  # ЕГАИС, Меркурий
    },
    {
        'id': 7004,
        'title': 'ИП Жумаев Азизбек Толиб угли 732790489214',
        'stageId': 'DT1070_38:UC_B7P2X4',
        'uf_crm_20_1747732557645': 123456789,
        'uf_crm_20_1763475932592': ['NO_MERCURY_PLATFORM'],
        'uf_crm_20_1739184606910': ['8432'],
    },
]


def parse_bitrix_item(item):
    """Парсит элемент Bitrix в удобный формат"""
    telegram_raw = item.get('uf_crm_20_1747732557645')
    
    # Извлекаем Telegram ID
    if telegram_raw:
        try:
            telegram_id = int(telegram_raw)
        except (ValueError, TypeError):
            telegram_id = None
    else:
        telegram_id = None
    
    # Маппинг продуктов
    product_id_map = {
        '8426': 'ЕГАИС',
        '8428': 'NAKLADNIE',
        '8430': 'YZEDO',
        '8432': 'MERCURY',
        '8434': 'MARKING',
    }
    
    product_ids = item.get('uf_crm_20_1739184606910', [])
    product_codes = [product_id_map.get(pid, pid) for pid in product_ids]
    
    return {
        'bitrix_id': item.get('id'),
        'title': item.get('title'),
        'company_name': item.get('title', 'Клиент'),
        'telegram_chat_id': telegram_id,
        'stage_id': item.get('stageId'),
        'wait_reasons': item.get('uf_crm_20_1763475932592', []),
        'product_codes': product_codes,
    }


def build_reminder_message(client_data):
    """Формирует сообщение напоминания"""
    REASON_NAMES = {
        'NO_UKEP': 'Нет УКЭП',
        'NO_JACARTA': 'Не загружен сертификат JaCarta',
        'NO_MERCURY_PLATFORM': 'Не подтверждена площадка в Меркурий',
        'NO_TRADE_HALL': 'Не заполнен торговый зал',
    }
    
    RISK_MESSAGES = {
        'NO_UKEP': 'Не сможете подписывать документы УКЭП',
        'NO_JACARTA': 'Риск штрафа при проверке',
        'NO_MERCURY_PLATFORM': 'Не сможете гасить ВСД — задержки поставок',
        'NO_TRADE_HALL': 'Не сможете списывать алкоголь по кассе',
    }
    
    FEATURES_BY_PRODUCT = {
        'ЕГАИС': ['Приём накладных в ЕГАИС', 'Просмотр остатков по пиву'],
        'Меркурий': ['Гашение ВСД', 'Просмотр сертификатов'],
        'Маркировка': ['Приём маркированных товаров', 'Вывод из оборота'],
        'YZEDO': ['Получение электронных накладных', 'Подписание УКЭП'],
    }
    
    lines = [
        f"🔍 <b>{client_data['company_name']}</b>, напоминаем о шагах!",
        "",
        "✅ УЖЕ ДОСТУПНО:",
    ]
    
    for product in client_data['product_codes']:
        features = FEATURES_BY_PRODUCT.get(product, [])
        for feature in features:
            lines.append(f"• {feature}")
    
    lines.append("")
    lines.append("⏳ ОСТАЛОСЬ СДЕЛАТЬ:")
    
    for reason_code in client_data['wait_reasons']:
        reason_name = REASON_NAMES.get(reason_code, reason_code)
        risk = RISK_MESSAGES.get(reason_code, 'Риск не определён')
        lines.append(f"• {reason_name} → {risk}")
    
    lines.append("")
    lines.append("💡 ЭТО ВАЖНО, ПОТОМУ ЧТО:")
    lines.append("Без этих шагов вы не сможете полноценно использовать систему.")
    lines.append("")
    lines.append("<i>Бот напоминаний Bitrix24</i>")
    
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
            return data.get("ok"), data


async def main():
    print("="*70)
    print("ФИНАЛЬНЫЙ ТЕСТ: Bitrix24 -> Telegram Integration")
    print("="*70)
    
    # Шаг 1: Имитация polling Bitrix24
    print("\n[1] Опрос Bitrix24 (polling)...")
    print(f"    Найдено элементов: {len(MOCK_BITRIX_ITEMS)}")
    
    # Шаг 2: Парсинг элементов
    print("\n[2] Парсинг элементов:")
    parsed_clients = []
    
    for item in MOCK_BITRIX_ITEMS:
        parsed = parse_bitrix_item(item)
        parsed_clients.append(parsed)
        print(f"    + ID={parsed['bitrix_id']}, Telegram={parsed['telegram_chat_id']}, "
              f"Продукты={parsed['product_codes']}")
    
    # Шаг 3: Отправка сообщений
    print("\n[3] Отправка напоминаний:")
    
    for client in parsed_clients:
        if not client['telegram_chat_id']:
            print(f"    - Пропуск (нет Telegram): {client['company_name']}")
            continue
        
        message = build_reminder_message(client)
        success, result = await send_telegram_message(client['telegram_chat_id'], message)
        
        if success:
            msg_id = result.get('result', {}).get('message_id')
            print(f"    [OK] Отправлено {client['company_name'][:40]}... (msg_id={msg_id})")
        else:
            error = result.get('description', 'Unknown error')
            print(f"    [ERROR] {client['company_name'][:40]}...: {error}")
    
    print("\n" + "="*70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("="*70)
    
    print("\n[INFO] Logika raboty planirovshchika (9:00 MSK):")
    print("  1. Opros Bitrix24 API -> poluchenie elementov na stadiyakh ozhidaniya")
    print("  2. Sinkhronizatsiya s lokalnoy BD (kliyenty, deal_states)")
    print("  3. Dlya kazhdogo aktivnogo kliyenta:")
    print("     - Proverka limita napominaniy (< 30)")
    print("     - Proverka: ne otpravlyali li segodnya")
    print("     - Otpravka soobshcheniya v Telegram")
    print("     - Obnovlenie schetchika v BD")
    
    print("\n[INFO] Dlya polnoy integratsii nuzhno:")
    print("  1. Proverit prava webhook na chtenie UF-poley Bitrix24")
    print("  2. Ili ispolzovat OAuth2 s pravami administratora")
    print("  3. Ubeditsya, chto v Bitrix24 zapolneny polya:")
    print("     - Telegram chat (UF_CRM_20_1747732557645)")
    print("     - Prichiny ozhidaniya (UF_CRM_20_1763475932592)")
    print("     - Produkty (UF_CRM_20_1739184606910)")


if __name__ == "__main__":
    asyncio.run(main())
