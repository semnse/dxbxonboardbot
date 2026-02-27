"""
MCP Server for Telegram Bot Testing
Provides tools for AI agents to test Telegram bot functionality
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

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')


class TelegramMCPServer:
    """MCP Server for Telegram Bot"""
    
    def __init__(self):
        self.tools = {
            "send_message": self.send_message,
            "get_updates": self.get_updates,
            "simulate_command": self.simulate_command,
            "get_chat_info": self.get_chat_info
        }
    
    async def send_message(self, chat_id: int, text: str) -> dict:
        """Send message to chat"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                return {
                    "success": data.get("ok", False),
                    "message_id": data.get("result", {}).get("message_id"),
                    "error": data.get("description") if not data.get("ok") else None
                }
    
    async def get_updates(self, offset: int = 0, limit: int = 10) -> list:
        """Get bot updates"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        params = {
            "offset": offset,
            "limit": limit,
            "timeout": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                return data.get("result", [])
    
    async def simulate_command(self, chat_id: int, command: str) -> dict:
        """Simulate user command (for testing)"""
        # Just send the command as a message
        return await self.send_message(chat_id, command)
    
    async def get_chat_info(self, chat_id: int) -> dict:
        """Get chat information"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
        params = {"chat_id": chat_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as response:
                data = await response.json()
                if data.get("ok"):
                    result = data.get("result", {})
                    return {
                        "id": result.get("id"),
                        "type": result.get("type"),
                        "title": result.get("title"),
                        "username": result.get("username"),
                        "members_count": result.get("members_count")
                    }
                else:
                    return {"error": data.get("description")}
    
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
    server = TelegramMCPServer()
    
    print("Telegram MCP Server")
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
