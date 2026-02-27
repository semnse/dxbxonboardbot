# 🤖 AI AGENT WORKFLOW FOR DXBX ONBOARDING BOT

**Alternative to MCP - Using Claude Desktop with Custom Tools**

---

## 📦 INSTALLATION

### 1. Install Claude Desktop

Download from: https://claude.ai/download

### 2. Install Python Dependencies

```bash
cd e:\Carrot1_WaitingClient
venv\Scripts\activate
pip install -r requirements.txt
```

---

## ⚙️ CONFIGURATION

### Configure Claude Desktop

File: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "e:\\Carrot1_WaitingClient"],
      "env": {
        "ALLOWED_DIRECTORIES": "app,tools,tests,docs"
      }
    },
    "database": {
      "command": "python",
      "args": ["e:\\Carrot1_WaitingClient\\tools\\mcp_database_server.py"],
      "env": {
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/onboarding_bot"
      }
    },
    "bitrix24": {
      "command": "python",
      "args": ["e:\\Carrot1_WaitingClient\\tools\\mcp_bitrix24_server.py"],
      "env": {
        "BITRIX_WEBHOOK_URL": "https://docsinbox.bitrix24.ru/rest/100398/cu1jtnas2sy621t3/"
      }
    },
    "telegram": {
      "command": "python",
      "args": ["e:\\Carrot1_WaitingClient\\tools\\mcp_telegram_server.py"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "8507378489:AAHKHl8UPnZgvP800WPofp7brrzDLuBXp0c"
      }
    }
  }
}
```

---

## 🛠 CREATE DATABASE MCP SERVER

File: `tools/mcp_database_server.py`

```python
"""
MCP Server for PostgreSQL Database
"""
import asyncio
import json
import os
import sys
from pathlib import Path

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


class DatabaseMCPServer:
    """MCP Server for PostgreSQL"""
    
    def __init__(self):
        self.tools = {
            "query": self.query,
            "list_tables": self.list_tables,
            "describe_table": self.describe_table
        }
    
    async def query(self, sql: str) -> list:
        """Execute SQL query"""
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
        """
        return await self.query(sql)
    
    async def describe_table(self, table_name: str) -> list:
        """Get table schema"""
        sql = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
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
    server = DatabaseMCPServer()
    
    print("Database MCP Server")
    print("="*50)
    
    while True:
        try:
            line = input("\nEnter SQL (or 'quit'): ")
            if line.lower() == 'quit':
                break
            
            result = asyncio.run(server.query(line))
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        except Exception as e:
            print(f"Error: {e}")
```

---

## 🤖 AI AGENT WORKFLOWS

### Workflow 1: Get Product Stages

**User Request:**
```
Get product stages for card 18518
```

**Claude Desktop Actions:**
1. Use Bitrix24 MCP: `get_product_stages card_id=18518`
2. Parse result
3. Display formatted output

**Example:**
```python
# In Claude Desktop chat
from tools.mcp_bitrix24_server import Bitrix24MCPServer

server = Bitrix24MCPServer()
result = server.run_tool("get_product_stages", card_id=18518)
print(json.dumps(result, indent=2, ensure_ascii=False))
```

---

### Workflow 2: Test Database Connection

**User Request:**
```
Check if chat_bindings table exists
```

**Claude Desktop Actions:**
1. Use Database MCP: `list_tables`
2. Check if 'chat_bindings' in result
3. If exists, describe table

**Example:**
```python
# In Claude Desktop chat
from tools.mcp_database_server import DatabaseMCPServer

server = DatabaseMCPServer()
tables = server.run_tool("list_tables")
print(tables)

if 'chat_bindings' in [t['table_name'] for t in tables['result']]:
    schema = server.run_tool("describe_table", table_name='chat_bindings')
    print(schema)
```

---

### Workflow 3: Send Test Message

**User Request:**
```
Send test message to chat 365611506
```

**Claude Desktop Actions:**
1. Use Telegram MCP: `send_message`
2. Verify success
3. Report result

**Example:**
```python
# In Claude Desktop chat
from tools.mcp_telegram_server import TelegramMCPServer

server = TelegramMCPServer()
result = server.run_tool(
    "send_message",
    chat_id=365611506,
    text="Test from AI Agent"
)
print(result)
```

---

## 📝 ALTERNATIVE: SIMPLE PYTHON SCRIPTS

If MCP is too complex, use simple Python scripts:

### Script 1: Get Card Info

File: `tools/ai_get_card.py`

```python
"""Simple script for AI to get card info"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.bitrix_product_service import BitrixProductService

async def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/ai_get_card.py <card_id>")
        sys.exit(1)
    
    card_id = int(sys.argv[1])
    service = BitrixProductService()
    
    stages = await service.get_product_stages(card_id)
    
    print(f"Card {card_id} Product Stages:")
    print("-" * 50)
    for stage in stages:
        print(f"  {stage['product_name']}: {stage['stage_name']}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Usage:**
```bash
python tools/ai_get_card.py 18518
```

---

## 🚀 QUICK START

### Option 1: Claude Desktop with MCP

1. Install Claude Desktop
2. Configure `claude_desktop_config.json`
3. Launch Claude Desktop
4. Use MCP tools in chat

### Option 2: Simple Python Scripts

1. Navigate to project root
2. Activate venv
3. Run scripts directly

```bash
python tools/ai_get_card.py 18518
python tools/mcp_bitrix24_server.py
python tools/mcp_telegram_server.py
```

---

## 📚 RESOURCES

- Claude Desktop: https://claude.ai/download
- MCP Documentation: https://modelcontextprotocol.io/
- Project GitHub: https://github.com/semnse/dxbxonboardbot

---

**Created:** 27.02.2026  
**DXBX AI Team**
