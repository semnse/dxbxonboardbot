"""Поиск и отправка сообщения с правильными причинами ожидания"""
import asyncio
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

import aiohttp
from app.services.telegram_service import TelegramService

WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")

# Маппинг причин ожидания (ID -> Текст)
# Эти ID нужно получить из Bitrix24 (справочник wait_reasons)
WAIT_REASON_MAP = {
    '21098': 'Завести номенклатуру в учётную систему',
    '21082': 'Подтверждение площадки в Меркурий',
    'NO_UKEP': 'Нет УКЭП',
    'NO_JACARTA': 'Не загружен сертификат JaCarta',
    'NO_MERCURY_PLATFORM': 'Не подтверждена площадка в Меркурий',
    'NO_TRADE_HALL': 'Не заполнен торговый зал',
    'NO_NOMENKLATURA_MAPPING': 'Не проведено сопоставление номенклатуры',
    'NO_YZEDO_SUPPLIERS': 'Не подключены поставщики в ЮЗЭДО',
    'NO_GTIN_BINDING': 'Не привязан GTIN к номенклатуре',
    'NO_TRAINING_DATE': 'Не назначена дата обучения',
}

# Маппинг продуктов (ID -> Название)
PRODUCT_MAP = {
    '8426': 'ЕГАИС',
    '8428': 'Накладные',
    '8430': 'ЮЗЭДО',
    '8432': 'Меркурий',
    '8434': 'Маркировка',
}


async def search_company(company_keyword: str):
    """Поиск компании по ключевому слову"""
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    params = {
        "entityTypeId": 1070,
        "filter": {"title": f"%{company_keyword}%"},
        "select": ["id", "title", "stageId"],
        "limit": 20
    }
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(url, data=json_data, headers={"Content-Type": "application/json"}) as response:
            text = await response.text()
            data = json.loads(text)
            
            if data.get('result'):
                return data['result'].get('items', [])
            return []


async def get_full_item(item_id: int):
    """Получение полного элемента с UF-полями"""
    url = f"{WEBHOOK_URL}/crm.item.get.json"
    
    params = {
        "entityTypeId": 1070,
        "id": item_id
    }
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(url, data=json_data, headers={"Content-Type": "application/json"}) as response:
            text = await response.text()
            data = json.loads(text)
            
            if data.get('result'):
                return data['result'].get('item', {})
            return None


def format_wait_reasons(reason_ids: list) -> list:
    """Преобразует ID причин ожидания в текст"""
    if not reason_ids:
        return []
    
    reasons = []
    for reason_id in reason_ids:
        # Пробуем найти в маппинге
        reason_text = WAIT_REASON_MAP.get(str(reason_id))
        
        if not reason_text:
            # Если не нашли, используем ID
            reason_text = f"Причина #{reason_id}"
        
        reasons.append(reason_text)
    
    return reasons


def format_products(product_ids: list) -> list:
    """Преобразует ID продуктов в названия"""
    if not product_ids:
        return []
    
    products = []
    for prod_id in product_ids:
        product_name = PRODUCT_MAP.get(str(prod_id))
        
        if product_name:
            products.append(product_name)
        else:
            products.append(f"Продукт #{prod_id}")
    
    return products


async def main():
    print("="*70)
    print("ПОИСК ООО \"ВАМС\" И ОТПРАВКА СООБЩЕНИЯ (с причинами)")
    print("="*70)
    
    # 1. Поиск компании
    print("\n[1] Поиск компании \"Вамс\"...")
    items = await search_company("Вамс")
    
    if not items:
        print("    [ERROR] Не найдено компаний с таким названием")
        return
    
    print(f"    Найдено элементов: {len(items)}")
    
    # 2. Получаем полные данные
    target_item = items[0]
    print(f"\n[2] Получение полных данных для ID={target_item.get('id')}...")
    
    full_item = await get_full_item(target_item['id'])
    
    if not full_item:
        print("    [ERROR] Не удалось получить полные данные")
        return
    
    # 3. Извлекаем данные
    print("\n[3] Данные из Bitrix24:")
    
    company_name = full_item.get('title', 'Клиент')
    inn = full_item.get('ufCrm20_1738855110463', 'не указан')
    telegram_chat = full_item.get('ufCrm20_1747732557645')
    stage = full_item.get('stageId', 'unknown')
    
    # Получаем сырые ID
    raw_products = full_item.get('ufCrm20_1739184606910', [])
    raw_wait_reasons = full_item.get('ufCrm20_1763475932592', [])
    
    # Преобразуем в текст
    products = format_products(raw_products)
    wait_reasons = format_wait_reasons(raw_wait_reasons)
    
    print(f"    Компания: {company_name}")
    print(f"    ИНН: {inn}")
    print(f"    Продукты: {products}")
    print(f"    Причины ожидания: {wait_reasons}")
    
    # 4. Формируем персонализированное сообщение
    print("\n[4] Формирование сообщения...")
    
    # Формируем блок "Осталось сделать"
    action_items = []
    for reason in wait_reasons:
        action_items.append(f"• {reason}")
    
    # Формируем блок "Продукты"
    product_lines = []
    for product in products:
        product_lines.append(f"• {product}")
    
    message = f"""
🔍 <b>Персональный отчёт для {company_name}</b>

📋 <b>Данные из Bitrix24:</b>
• ИНН: {inn}
• Стадия: {stage}

✅ <b>Подключённые продукты:</b>
{chr(10).join(product_lines) if product_lines else '• Не указаны'}

⏳ <b>Осталось сделать:</b>
{chr(10).join(action_items) if action_items else '• Нет активных задач'}

💡 <b>Важно:</b>
Без выполнения этих шагов вы не сможете полноценно использовать систему.
Это может привести к ошибкам в отчётности и проблемам с контролирующими органами.

---
<i>Бот онбординга Bitrix24</i>
"""
    
    print("    Soobshchenie sformirovano")
    print(f"\n    Tekst soobshcheniya:")
    print("    " + "-"*60)
    # Vyvodim bez HTML tegov
    plain_text = message.replace("<b>", "").replace("</b>", "") \
        .replace("<i>", "").replace("</i>", "") \
        .replace("🔍", "[INFO]") \
        .replace("📋", "[INFO]") \
        .replace("✅", "[OK]") \
        .replace("⏳", "[WAIT]") \
        .replace("💡", "[TIP]")
    for line in plain_text.split('\n')[:20]:
        print(f"    {line.encode('cp1251', errors='replace').decode('cp1251')}")
    print("    " + "-"*60)
    
    # 5. Otpravlyaem soobshchenie
    print("\n[5] Otpravka soobshcheniya v Telegram...")
    
    YOUR_CHAT_ID = 365611506
    
    telegram = TelegramService()
    result = await telegram.send_message(YOUR_CHAT_ID, message)
    
    if result.ok:
        print(f"    [OK] Soobshchenie otpravleno! (msg_id={result.message_id})")
        print(f"    Proverte Telegram chat {YOUR_CHAT_ID}")
    else:
        print(f"    [ERROR] {result.description}")
    
    print("\n" + "="*70)
    print("GOTOVO")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
