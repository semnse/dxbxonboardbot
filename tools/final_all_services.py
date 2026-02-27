"""Финальный тест: Поиск и отправка сообщения с использованием всех сервисов"""
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
from app.services.bitrix_stage_service import BitrixStageService

WEBHOOK_URL = os.environ.get("BITRIX_WEBHOOK_URL", "")

PRODUCT_MAP = {
    '8426': 'ЕГАИС',
    '8428': 'Накладные',
    '8430': 'ЮЗЭДО',
    '8432': 'Меркурий',
    '8434': 'Маркировка',
}


async def search_company(company_keyword: str):
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
    url = f"{WEBHOOK_URL}/crm.item.get.json"
    params = {"entityTypeId": 1070, "id": item_id}
    
    async with aiohttp.ClientSession() as session:
        json_data = json.dumps(params, ensure_ascii=False)
        async with session.post(url, data=json_data, headers={"Content-Type": "application/json"}) as response:
            text = await response.text()
            data = json.loads(text)
            if data.get('result'):
                return data['result'].get('item', {})
            return None


def format_products(product_ids: list) -> list:
    if not product_ids:
        return []
    return [PRODUCT_MAP.get(str(pid), f"Продукт #{pid}") for pid in product_ids]


async def main():
    print("="*70)
    print("FINAL TEST: Bitrix24 -> Telegram (all services)")
    print("="*70)
    
    # 1. Search company
    print("\n[1] Search company \"Vams\"...")
    items = await search_company("Вамс")
    
    if not items:
        print("    [ERROR] Not found")
        return
    
    print(f"    Found: {len(items)}")
    
    # 2. Get full item
    target_item = items[0]
    print(f"\n[2] Get full data for ID={target_item.get('id')}...")
    
    full_item = await get_full_item(target_item['id'])
    
    if not full_item:
        print("    [ERROR] Failed to get full data")
        return
    
    # 3. Extract data
    print("\n[3] Data from Bitrix24:")
    
    company_name = full_item.get('title', 'Client')
    inn = full_item.get('ufCrm20_1738855110463', 'N/A')
    stage_id = full_item.get('stageId', 'unknown')
    
    # Map stage
    stage_name = BitrixStageService.get_stage_name(stage_id)
    is_wait = BitrixStageService.is_wait_stage(stage_id)
    wait_reason = BitrixStageService.get_wait_stage_reason(stage_id)
    
    raw_products = full_item.get('ufCrm20_1739184606910', [])
    raw_wait_reasons = full_item.get('ufCrm20_1763475932592', [])
    
    products = format_products(raw_products)
    action_items = WaitReasonsService.format_action_items(raw_wait_reasons)
    general_risk = WaitReasonsService.get_general_risk(raw_wait_reasons, raw_products)
    
    print(f"    Company: {company_name[:60]}")
    print(f"    INN: {inn}")
    print(f"    Stage: {stage_id}")
    print(f"    Stage Name: {stage_name}")
    print(f"    Is Wait Stage: {is_wait}")
    print(f"    Wait Reason: {wait_reason}")
    print(f"    Products: {products}")
    print(f"    Action Items: {len(action_items)}")
    for action, risk in action_items:
        print(f"      - {action}")
    
    # 4. Build message
    print("\n[4] Building message...")
    
    product_lines = [f"• {p}" for p in products]
    action_lines = [f"• {action}" for action, _ in action_items]
    
    message = f"""
🔍 <b>Personalnyy otchet dlya {company_name}</b>

📋 <b>Dannye iz Bitrix24:</b>
• INN: {inn}
• Stadiya: {stage_name}

✅ <b>Podklyuchennye produkty:</b>
{chr(10).join(product_lines) if product_lines else '• Ne ukazany'}

⏳ <b>Ostalos sdelat:</b>
{chr(10).join(action_lines) if action_lines else '• Net aktivnykh zadach'}

💡 <b>Eto vazhno, potomu chto:</b>
{general_risk}

---
<i>Bot onbordinga Bitrix24</i>
"""
    
    print("    Message built")
    
    # 5. Send
    print("\n[5] Sending to Telegram...")
    
    YOUR_CHAT_ID = 365611506
    telegram = TelegramService()
    result = await telegram.send_message(YOUR_CHAT_ID, message)
    
    if result.ok:
        print(f"    [OK] Sent! (msg_id={result.message_id})")
    else:
        print(f"    [ERROR] {result.description}")
    
    print("\n" + "="*70)
    print("DONE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
