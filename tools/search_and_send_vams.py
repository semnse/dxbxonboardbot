"""Поиск и отправка сообщения для ООО Вамс"""
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


async def search_company(company_keyword: str):
    """Поиск компании по ключевому слову"""
    url = f"{WEBHOOK_URL}/crm.item.list.json"
    
    # Ищем по всем стадиям
    params = {
        "entityTypeId": 1070,
        "filter": {"title": f"%{company_keyword}%"},  # Поиск по названию
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


async def main():
    print("="*70)
    print("ПОИСК ООО \"ВАМС\" И ОТПРАВКА СООБЩЕНИЯ")
    print("="*70)
    
    # 1. Поиск компании
    print("\n[1] Поиск компании \"Вамс\"...")
    items = await search_company("Вамс")
    
    if not items:
        print("    [ERROR] Не найдено компаний с таким названием")
        return
    
    print(f"    Найдено элементов: {len(items)}")
    
    # 2. Вывод найденных
    print("\n[2] Найденные элементы:")
    for i, item in enumerate(items, 1):
        print(f"    {i}. ID={item.get('id')}, Title={item.get('title', '')[:60]}")
    
    # 3. Получаем полные данные для первого элемента
    target_item = items[0]
    print(f"\n[3] Получение полных данных для ID={target_item.get('id')}...")
    
    full_item = await get_full_item(target_item['id'])
    
    if not full_item:
        print("    [ERROR] Не удалось получить полные данные")
        return
    
    # 4. Вывод всех полей
    print("\n[4] Полные данные элемента:")
    print(f"    ID: {full_item.get('id')}")
    print(f"    Название: {full_item.get('title')}")
    print(f"    Стадия: {full_item.get('stageId')}")
    
    # Ключевые UF-поля
    uf_fields = {
        'Telegram': 'ufCrm20_1747732557645',
        'ИНН': 'ufCrm20_1738855110463',
        'Компания (юр.лицо)': 'ufCrm20_1744289908193',
        'Продукты': 'ufCrm20_1739184606910',
        'Причины ожидания': 'ufCrm20_1763475932592',
    }
    
    print("\n    UF-поля:")
    for name, field in uf_fields.items():
        value = full_item.get(field)
        print(f"      {name}: {value}")
    
    # 5. Формируем персонализированное сообщение
    print("\n[5] Формирование персонализированного сообщения...")
    
    company_name = full_item.get('title', 'Клиент')
    inn = full_item.get('ufCrm20_1738855110463', 'не указан')
    telegram_chat = full_item.get('ufCrm20_1747732557645')
    stage = full_item.get('stageId', 'unknown')
    
    message = f"""
🔍 <b>Персональный отчёт для {company_name}</b>

📋 <b>Данные из Bitrix24:</b>
• ИНН: {inn}
• Стадия: {stage}
• Telegram: {telegram_chat or 'не указан'}

✅ <b>Статус внедрения:</b>
Ваша торговая точка находится в процессе внедрения.

⏳ <b>Следующие шаги:</b>
• Проверьте заполненность всех полей
• Пройдите обучение по системе
• Запустите пилотную работу

💡 <b>Важно:</b>
Если у вас возникнут вопросы — обратитесь к вашему менеджеру внедрения.

---
<i>Бот онбординга Bitrix24</i>
"""
    
    print("    Сообщение сформировано")
    
    # 6. Отправляем сообщение
    print("\n[6] Отправка сообщения в Telegram...")
    
    # Ваш chat_id для получения отчёта
    YOUR_CHAT_ID = 365611506
    
    telegram = TelegramService()
    result = await telegram.send_message(YOUR_CHAT_ID, message)
    
    if result.ok:
        print(f"    [OK] Сообщение отправлено! (msg_id={result.message_id})")
        print(f"    Проверьте Telegram чат {YOUR_CHAT_ID}")
    else:
        print(f"    [ERROR] {result.description}")
    
    print("\n" + "="*70)
    print("ГОТОВО")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
