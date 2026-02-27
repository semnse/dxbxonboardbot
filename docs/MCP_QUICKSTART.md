# 🚀 MCP ORCHESTRATION QUICK START

**Quick Start Guide for AI Agents working on DXBX Onboarding Bot**

---

## 📦 INSTALLATION

### 1. Install Node.js (for MCP CLI)

Download from: https://nodejs.org/

### 2. Install MCP CLI

```bash
npm install -g @modelcontextprotocol/cli
```

### 3. Install Python Dependencies

```bash
cd e:\Carrot1_WaitingClient
venv\Scripts\activate
pip install -r requirements.txt
```

---

## ⚙️ CONFIGURATION

### 1. Configure MCP Servers

File: `mcp_config.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "e:\\Carrot1_WaitingClient"]
    },
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://postgres:postgres@localhost:5432/onboarding_bot"]
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "e:\\Carrot1_WaitingClient"]
    },
    "terminal": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-terminal"]
    },
    "bitrix24": {
      "command": "python",
      "args": ["tools/mcp_bitrix24_server.py"]
    },
    "telegram": {
      "command": "python",
      "args": ["tools/mcp_telegram_server.py"]
    }
  }
}
```

---

## 🤖 START AI AGENTS

### Option 1: Manual Start

```bash
# Start File System Server
npx -y @modelcontextprotocol/server-filesystem e:\Carrot1_WaitingClient

# Start Database Server
npx -y @modelcontextprotocol/server-postgres postgresql://postgres:postgres@localhost:5432/onboarding_bot

# Start Git Server
npx -y @modelcontextprotocol/server-git e:\Carrot1_WaitingClient

# Start Terminal Server
npx -y @modelcontextprotocol/server-terminal

# Start Bitrix24 Server (custom)
python tools/mcp_bitrix24_server.py

# Start Telegram Server (custom)
python tools/mcp_telegram_server.py
```

### Option 2: Use MCP Orchestrator

```bash
mcp-orchestrator --config mcp_config.json
```

---

## 📖 USAGE EXAMPLES

### Example 1: Get Card from Bitrix24

**Via Terminal:**
```bash
python tools/mcp_bitrix24_server.py
```

**Then enter:**
```
get_card card_id=18518
```

**Result:**
```json
{
  "success": true,
  "result": {
    "id": 18518,
    "title": "ООО \"М7\" 7802964436 Мойка 7 бар",
    "stageId": "DT1070_38:UC_IM0YI8"
  }
}
```

---

### Example 2: Get Product Stages

**Via Terminal:**
```bash
python tools/mcp_bitrix24_server.py
```

**Then enter:**
```
get_product_stages card_id=18518
```

**Result:**
```json
{
  "success": true,
  "result": [
    {"id": 69540, "product": "ЕГАИС", "category_id": 22, "stage_id": "DT1056_22:UC_FNNCDK"},
    {"id": 69544, "product": "Накладные", "category_id": 24, "stage_id": "DT1056_24:UC_8MO9Q3"},
    {"id": 69546, "product": "Маркировка", "category_id": 28, "stage_id": "DT1056_28:UC_LC9J27"},
    {"id": 69548, "product": "ЮЗЭДО", "category_id": 26, "stage_id": "DT1056_26:2"}
  ]
}
```

---

### Example 3: Send Telegram Message

**Via Terminal:**
```bash
python tools/mcp_telegram_server.py
```

**Then enter:**
```
send_message chat_id=365611506 text="Test from MCP"
```

**Result:**
```json
{
  "success": true,
  "result": {
    "message_id": 123,
    "error": null
  }
}
```

---

## 🔄 AI AGENT WORKFLOWS

### Workflow: Add New Feature

1. **Developer Agent** reads existing code:
   ```
   filesystem.read_file path="app/services/bitrix_product_service.py"
   ```

2. **Developer Agent** writes new feature:
   ```
   filesystem.write_file path="app/api/routes/cards.py" content="..."
   ```

3. **Testing Agent** runs tests:
   ```
   terminal.execute command="pytest tests/test_product_service.py"
   ```

4. **DevOps Agent** commits changes:
   ```
   git.commit message="feat: Add product stages endpoint"
   ```

---

## 📝 LOGS

All MCP interactions are logged to:
```
logs/mcp_orchestrator.log
```

View logs:
```bash
tail -f logs/mcp_orchestrator.log
```

---

## 🛠 TROUBLESHOOTING

### Issue: MCP Server not starting

**Solution:**
```bash
# Check Node.js version
node --version

# Reinstall MCP CLI
npm uninstall -g @modelcontextprotocol/cli
npm install -g @modelcontextprotocol/cli
```

### Issue: Database connection failed

**Solution:**
```bash
# Check PostgreSQL is running
sc query postgresql-x64-15

# Test connection
python tools/check_db_connection.py
```

### Issue: Bitrix24 server not responding

**Solution:**
```bash
# Test Bitrix24 connection
python tools/mcp_bitrix24_server.py
get_card card_id=18518
```

---

## 📚 DOCUMENTATION

- Full MCP documentation: `docs/MCP_ORCHESTRATION.md`
- Project documentation: `docs/IMPLEMENTATION_GUIDE.md`
- Bot instructions: `docs/BOT_INSTRUCTIONS.md`

---

**Created:** 27.02.2026  
**DXBX AI Team**
