"""Прямая проверка подключения к PostgreSQL"""
import asyncio
import asyncpg


async def check():
    print("="*70)
    print("ПРОВЕРКА POSTGRESQL")
    print("="*70)
    
    try:
        # Пробуем подключиться напрямую
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="onboarding_bot"
        )
        
        print("\n[OK] Подключение успешно!")
        
        # Проверяем таблицы
        rows = await conn.fetch("SELECT COUNT(*) FROM clients")
        print(f"[INFO] Клиентов в БД: {rows[0][0]}")
        
        rows = await conn.fetch("SELECT COUNT(*) FROM deal_states")
        print(f"[INFO] Состояний сделок: {rows[0][0]}")
        
        # Показываем клиентов
        clients = await conn.fetch("SELECT id, company_name, telegram_chat_id FROM clients LIMIT 5")
        if clients:
            print("\n[INFO] Последние клиенты:")
            for c in clients:
                print(f"  - ID={c['id']}, {c['company_name']}, Telegram: {c['telegram_chat_id'] or 'не указан'}")
        
        await conn.close()
        print("\n[OK] Тест пройден!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    asyncio.run(check())
