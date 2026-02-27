"""Применение миграции chat_bindings"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    env_values = dotenv_values(str(env_path))
    for key, value in env_values.items():
        if value is not None:
            os.environ[key] = value

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/onboarding_bot")


async def main():
    print("="*70)
    print("MIGRATION: Add chat_bindings table")
    print("="*70)
    
    # Парсим DATABASE_URL
    # postgresql+asyncpg://postgres:postgres@localhost:5432/onboarding_bot
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"\n[INFO] Connecting to DB: {db_url[:50]}...")
    
    try:
        conn = await asyncpg.connect(db_url)
        print("[OK] Connected")
        
        # Создаём таблицу
        print("\n[INFO] Creating table chat_bindings...")
        
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
        
        print("[OK] Table created")
        
        # Создаём индексы
        print("\n[INFO] Creating indexes...")
        
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_bindings_chat_id ON chat_bindings(chat_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_bindings_bitrix_deal_id ON chat_bindings(bitrix_deal_id)")
        
        print("[OK] Indexes created")
        
        await conn.close()
        
        print("\n" + "="*70)
        print("MIGRATION COMPLETED")
        print("="*70)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
