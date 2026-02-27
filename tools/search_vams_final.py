"""Поиск и отправка сообщения с правильными причинами и рисками"""
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
from app.services.wait_reasons_service import WaitReasonsService

WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")

# Маппинг продуктов
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
    print("POISK I OTPRAVKA S PRAVILNYMI PRICHINAMI I RISKAMI")
    print("="*70)
    
    # 1. Поиск компании
    print("\n[1] Poisk kompanii \"Vams\"...")
    items = await search_company("Вамс")
    
    if not items:
        print("    [ERROR] Ne naideno kompaniy")
        return
    
    print(f"    Naideno elementov: {len(items)}")
    
    # 2. Poluchaem polnye dannye
    target_item = items[0]
    print(f"\n[2] Poluchenie polnykh dannykh dlya ID={target_item.get('id')}...")
    
    full_item = await get_full_item(target_item['id'])
    
    if not full_item:
        print("    [ERROR] Ne udalos poluchit polnye dannye")
        return
    
    # 3. Izbekaem dannye
    print("\n[3] Dannye iz Bitrix24:")
    
    company_name = full_item.get('title', 'Klient')
    inn = full_item.get('ufCrm20_1738855110463', 'ne ukazan')
    stage = full_item.get('stageId', 'unknown')
    
    # Syrye ID
    raw_products = full_item.get('ufCrm20_1739184606910', [])
    raw_wait_reasons = full_item.get('ufCrm20_1763475932592', [])
    
    # Preobrazuem
    products = format_products(raw_products)
    
    # Ispolzuem servis prichin
    action_items = WaitReasonsService.format_action_items(raw_wait_reasons)
    general_risk = WaitReasonsService.get_general_risk(raw_wait_reasons, raw_products)
    
    print(f"    Kompaniya: {company_name}")
    print(f"    INN: {inn}")
    print(f"    Produkty: {products}")
    print(f"    Prichiny ozhidaniya: {len(action_items)} sht.")
    for action, risk in action_items:
        print(f"      - {action}")
    
    # 4. Formiruem soobshchenie
    print("\n[4] Formirovanie soobshcheniya...")
    
    # Blok "Produkty"
    product_lines = [f"• {p}" for p in products]
    
    # Blok "Ostalos sdelat"
    action_lines = [f"• {action}" for action, _ in action_items]
    
    message = f"""
🔍 <b>Personalnyy otchet dlya {company_name}</b>

📋 <b>Dannye iz Bitrix24:</b>
• INN: {inn}
• Stadiya: {stage}

✅ <b>Podklyuchennye produkty:</b>
{chr(10).join(product_lines) if product_lines else '• Ne ukazany'}

⏳ <b>Ostalos sdelat:</b>
{chr(10).join(action_lines) if action_lines else '• Net aktivnykh zadach'}

💡 <b>Eto vazhno, potomu chto:</b>
{general_risk}

---
<i>Bot onbordinga Bitrix24</i>
"""
    
    print("    Soobshchenie sformirovano")
    
    # 5. Otpravlyaem
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
