"""Проверка таблицы chat_bindings"""
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

async def main():
    print("="*70)
    print("ПРОВЕРКА ТАБЛИЦЫ chat_bindings")
    print("="*70)
    
    # Парсим DATABASE_URL
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/onboarding_bot')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print(f"\nПодключение: {db_url[:60]}...")
    
    try:
        conn = await asyncpg.connect(db_url)
        print("[OK] Подключено!")
        
        # Проверяем таблицу
        result = await conn.fetch("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'chat_bindings')")
        exists = result[0]['exists']
        
        if exists:
            print("[OK] Таблица chat_bindings существует!")
            
            # Считаем записи
            count = await conn.fetchval("SELECT COUNT(*) FROM chat_bindings")
            print(f"    Записей: {count}")
        else:
            print("[WARN] Таблица chat_bindings НЕ существует!")
            print("\nСоздаём таблицу...")
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_bindings (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL UNIQUE,
                    chat_title VARCHAR(255),
                    bitrix_deal_id VARCHAR(50) NOT NULL,
                    company_name VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            print("[OK] Таблица создана!")
        
        await conn.close()
        print("\n[OK] Готово!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(main())
