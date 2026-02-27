"""
MCP Server for Bitrix24 Integration
Provides tools for AI agents to interact with Bitrix24 API
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import dotenv_values
import aiohttp

# Load environment
env_path = Path(__file__).parent.parent / ".env"
env_values = dotenv_values(str(env_path))
for k, v in env_values.items():
    if v:
        os.environ[k] = v

WEBHOOK_URL = os.environ.get('BITRIX_WEBHOOK_URL', '').rstrip('/')


class Bitrix24MCPServer:
    """MCP Server for Bitrix24"""
    
    def __init__(self):
        self.tools = {
            "get_card": self.get_card,
            "get_product_stages": self.get_product_stages,
            "search_cards": self.search_cards,
            "get_stage_name": self.get_stage_name
        }
    
    async def get_card(self, card_id: int) -> dict:
        """Get card by ID"""
        url = f"{WEBHOOK_URL}/crm.item.get.json"
        params = {"entityTypeId": 1070, "id": card_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                return data.get('result', {}).get('item', {})
    
    async def get_product_stages(self, card_id: int) -> list:
        """Get product implementation stages for card"""
        url = f"{WEBHOOK_URL}/crm.item.list.json"
        params = {
            "entityTypeId": 1056,
            "filter": {"parentId1070": card_id},
            "select": ["id", "title", "stageId", "categoryId"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                items = data.get('result', {}).get('items', [])
                
                # Map categories to products
                category_map = {
                    22: 'ЕГАИС',
                    24: 'Накладные',
                    26: 'ЮЗЭДО',
                    28: 'Маркировка',
                    36: 'Меркурий'
                }
                
                result = []
                for item in items:
                    result.append({
                        'id': item.get('id'),
                        'product': category_map.get(item.get('categoryId'), 'Unknown'),
                        'category_id': item.get('categoryId'),
                        'stage_id': item.get('stageId'),
                        'title': item.get('title', '')[:50]
                    })
                
                return result
    
    async def search_cards(self, query: str, limit: int = 10) -> list:
        """Search cards by title"""
        url = f"{WEBHOOK_URL}/crm.item.list.json"
        params = {
            "entityTypeId": 1070,
            "filter": {"TITLE": f"%{query}%"},
            "select": ["id", "title", "stageId"],
            "limit": limit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                items = data.get('result', {}).get('items', [])
                return [
                    {
                        'id': item.get('id'),
                        'title': item.get('title', '')[:100],
                        'stage': item.get('stageId')
                    }
                    for item in items
                ]
    
    async def get_stage_name(self, stage_id: str) -> str:
        """Get human-readable stage name"""
        stage_names = {
            'DT1070_38:UC_IM0YI8': 'Пауза до вывода',
            'DT1070_38:UC_70SK2H': 'Чек работы системы',
            'DT1070_38:UC_B7P2X4': 'Выведена на MRR',
            'DT1070_38:UC_JK4IJR': 'Подключение поставщиков',
            'DT1070_38:SUCCESS': 'Успешно',
            'DT1070_38:FAIL': 'Провал',
        }
        return stage_names.get(stage_id, stage_id)
    
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
    server = Bitrix24MCPServer()
    
    print("Bitrix24 MCP Server")
    print("="*50)
    print("Available tools:")
    for tool in server.tools.keys():
        print(f"  - {tool}")
    print("="*50)
    
    while True:
        try:
            line = input("\nEnter command (or 'quit'): ")
            if line.lower() == 'quit':
                break
            
            parts = line.split()
            if len(parts) < 2:
                print("Usage: <tool_name> <arg1>=<value1> [arg2=<value2>...]")
                continue
            
            tool_name = parts[0]
            kwargs = {}
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    kwargs[key] = int(value) if value.isdigit() else value
            
            result = server.run_tool(tool_name, **kwargs)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
