"""Simple test for Database MCP Server"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values

# Load env
env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

import asyncpg

async def test():
    DATABASE_URL = os.environ.get('DATABASE_URL', '')
    # Fix URL for asyncpg
    if '+asyncpg' in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace('+asyncpg', '')
    
    print(f"Connecting to: {DATABASE_URL[:50]}...")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("[OK] Connected!")
        
        # List tables
        rows = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        print(f"\nTables ({len(rows)}):")
        for row in rows:
            print(f"  - {row['table_name']}")
        
        await conn.close()
        print("\n[OK] Disconnected")
        
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(test())
