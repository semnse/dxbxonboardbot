"""
MCP Server for PostgreSQL Database
Provides tools for AI agents to query the database
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values
import asyncpg

# Load environment
env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

DATABASE_URL = os.environ.get('DATABASE_URL', '')
# Fix URL for asyncpg (remove +asyncpg)
if '+asyncpg' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('+asyncpg', '')


class DatabaseMCPServer:
    """MCP Server for PostgreSQL"""
    
    def __init__(self):
        self.tools = {
            "query": self.query,
            "list_tables": self.list_tables,
            "describe_table": self.describe_table,
            "get_chat_bindings": self.get_chat_bindings
        }
    
    async def query(self, sql: str) -> list:
        """Execute SQL query"""
        if not sql.strip().upper().startswith('SELECT'):
            return {"error": "Only SELECT queries are allowed"}
        
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(sql)
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def list_tables(self) -> list:
        """List all tables"""
        sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        return await self.query(sql)
    
    async def describe_table(self, table_name: str) -> list:
        """Get table schema"""
        sql = f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(sql, table_name)
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def get_chat_bindings(self) -> list:
        """Get all chat bindings"""
        sql = """
            SELECT id, chat_id, chat_title, bitrix_deal_id, company_name, is_active, created_at
            FROM chat_bindings
            ORDER BY created_at DESC
        """
        return await self.query(sql)
    
    def run_tool(self, tool_name: str, **kwargs):
        """Run tool and return result"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            result = asyncio.run(self.tools[tool_name](**kwargs))
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    # Interactive mode for testing
    server = DatabaseMCPServer()
    
    print("Database MCP Server")
    print("="*50)
    print("Available tools:")
    for tool in server.tools.keys():
        print(f"  - {tool}")
    print("="*50)
    print("\nExample queries:")
    print("  list_tables")
    print("  describe_table table_name=clients")
    print("  query sql=SELECT * FROM clients LIMIT 5")
    print("  get_chat_bindings")
    print("="*50)
    
    while True:
        try:
            line = input("\nEnter command (or 'quit'): ")
            if line.lower() == 'quit':
                break
            
            parts = line.split(maxsplit=1)
            if len(parts) < 1:
                print("Usage: <tool_name> [arg1=value1 ...]")
                continue
            
            tool_name = parts[0]
            kwargs = {}
            
            if len(parts) > 1:
                for part in parts[1].split():
                    if '=' in part:
                        key, value = part.split('=', 1)
                        kwargs[key] = int(value) if value.isdigit() else value
            
            result = server.run_tool(tool_name, **kwargs)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
