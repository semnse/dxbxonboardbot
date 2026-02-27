"""Проверка таблицы chat_bindings (синхронно)"""
import os
from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

import psycopg2

print("="*70)
print("CHECK TABLE chat_bindings")
print("="*70)

db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/onboarding_bot')
db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

print(f"\nConnection: {db_url[:60]}...")

try:
    conn = psycopg2.connect(db_url)
    print("[OK] Подключено!")
    
    cur = conn.cursor()
    
    # Проверяем таблицу
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'chat_bindings')")
    exists = cur.fetchone()[0]
    
    if exists:
        print("[OK] Таблица chat_bindings существует!")
        
        cur.execute("SELECT COUNT(*) FROM chat_bindings")
        count = cur.fetchone()[0]
        print(f"    Записей: {count}")
    else:
        print("[WARN] Таблица chat_bindings НЕ существует!")
        print("\nСоздаём таблицу...")
        
        cur.execute("""
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
        
        conn.commit()
        print("[OK] Таблица создана!")
    
    cur.close()
    conn.close()
    print("\n[OK] Готово!")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
