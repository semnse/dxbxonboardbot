# 🤖 MCP ORCHESTRATION FOR DXBX ONBOARDING BOT

**Version:** 1.0  
**Date:** 27.02.2026  
**Project:** Telegram Onboarding Bot with Bitrix24 Integration

---

## 📋 CONTENTS

1. [Overview](#overview)
2. [MCP Servers](#mcp-servers)
3. [AI Agents](#ai-agents)
4. [Workflows](#workflows)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)

---

## 🎯 OVERVIEW

This document describes the MCP (Model Context Protocol) orchestration for AI agents working on the DXBX Onboarding Bot project.

### Architecture:

```
┌─────────────────────────────────────────────────────────┐
│                  MCP ORCHESTRATOR                        │
├─────────────────────────────────────────────────────────┤
│  AI Agent 1: Code Developer                              │
│  AI Agent 2: Database Specialist                         │
│  AI Agent 3: Testing Engineer                            │
│  AI Agent 4: DevOps Engineer                             │
│  AI Agent 5: Documentation Writer                        │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  MCP SERVERS                             │
├─────────────────────────────────────────────────────────┤
│  - File System Server (read/write code)                 │
│  - Database Server (PostgreSQL queries)                 │
│  - Git Server (version control)                         │
│  - Terminal Server (command execution)                  │
│  - Bitrix24 Server (API integration)                    │
│  - Telegram Server (bot testing)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 MCP SERVERS

### 1. File System Server

**Purpose:** Read/write project files

**Configuration:**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "e:\\Carrot1_WaitingClient"],
      "env": {
        "ALLOWED_DIRECTORIES": "app,tools,tests,docs"
      }
    }
  }
}
```

**Capabilities:**
- `read_file` - Read file contents
- `write_file` - Write file contents
- `list_directory` - List directory contents
- `search_files` - Search for files by pattern

---

### 2. Database Server

**Purpose:** Execute PostgreSQL queries

**Configuration:**
```json
{
  "mcpServers": {
    "database": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://postgres:postgres@localhost:5432/onboarding_bot"]
    }
  }
}
```

**Capabilities:**
- `query` - Execute SQL query
- `list_tables` - List all tables
- `describe_table` - Get table schema

---

### 3. Git Server

**Purpose:** Version control operations

**Configuration:**
```json
{
  "mcpServers": {
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "e:\\Carrot1_WaitingClient"],
      "env": {
        "GIT_AUTHOR_NAME": "DXBX AI Agent",
        "GIT_AUTHOR_EMAIL": "ai@dxbx.ru"
      }
    }
  }
}
```

**Capabilities:**
- `commit` - Commit changes
- `push` - Push to remote
- `pull` - Pull from remote
- `create_branch` - Create new branch
- `merge_branch` - Merge branches

---

### 4. Terminal Server

**Purpose:** Execute shell commands

**Configuration:**
```json
{
  "mcpServers": {
    "terminal": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-terminal"],
      "env": {
        "ALLOWED_COMMANDS": "python,pip,git,docker,uvicorn,pytest"
      }
    }
  }
}
```

**Capabilities:**
- `execute` - Execute command
- `run_script` - Run Python script
- `install_package` - Install Python package

---

### 5. Bitrix24 Server

**Purpose:** Interact with Bitrix24 API

**Configuration:**
```json
{
  "mcpServers": {
    "bitrix24": {
      "command": "python",
      "args": ["tools/mcp_bitrix24_server.py"],
      "env": {
        "BITRIX_WEBHOOK_URL": "https://docsinbox.bitrix24.ru/rest/100398/cu1jtnas2sy621t3/"
      }
    }
  }
}
```

**Capabilities:**
- `get_card` - Get card by ID
- `get_product_stages` - Get product implementation stages
- `update_stage` - Update card stage
- `search_cards` - Search cards by criteria

---

### 6. Telegram Server

**Purpose:** Test Telegram bot

**Configuration:**
```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["tools/mcp_telegram_server.py"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "8507378489:AAHKHl8UPnZgvP800WPofp7brrzDLuBXp0c"
      }
    }
  }
}
```

**Capabilities:**
- `send_message` - Send message to chat
- `get_updates` - Get bot updates
- `simulate_command` - Simulate user command

---

## 🤖 AI AGENTS

### Agent 1: Code Developer

**Role:** Write and modify code

**Specialization:**
- Python development
- FastAPI endpoints
- aiogram bot handlers
- Service layer implementation

**Tools:**
- `filesystem` (read/write)
- `terminal` (run tests)
- `git` (commit changes)

**Example Prompt:**
```
You are a senior Python developer working on DXBX Onboarding Bot.

Task: Add new feature to get product stages for card 18518.

Requirements:
1. Create service in app/services/bitrix_product_service.py
2. Add endpoint in app/api/routes/cards.py
3. Write tests in tests/test_product_service.py

Use MCP filesystem server to read/write files.
```

---

### Agent 2: Database Specialist

**Role:** Manage database schema and queries

**Specialization:**
- PostgreSQL optimization
- SQLAlchemy models
- Database migrations
- Query optimization

**Tools:**
- `database` (query execution)
- `filesystem` (read models)
- `terminal` (run migrations)

**Example Prompt:**
```
You are a database specialist optimizing PostgreSQL for DXBX Onboarding Bot.

Task: Add chat_bindings table for persistent chat-card bindings.

Requirements:
1. Create migration in migrations/002_add_chat_bindings.sql
2. Add ChatBinding model in app/database/models.py
3. Create repository in app/database/repository.py

Use MCP database server to test queries.
```

---

### Agent 3: Testing Engineer

**Role:** Write and run tests

**Specialization:**
- Unit tests (pytest)
- Integration tests
- End-to-end tests
- Test coverage analysis

**Tools:**
- `terminal` (run pytest)
- `filesystem` (read/write tests)
- `telegram` (simulate bot commands)

**Example Prompt:**
```
You are a testing engineer ensuring quality of DXBX Onboarding Bot.

Task: Write tests for BitrixProductService.

Requirements:
1. Test product stage retrieval for card 18518
2. Test Mercury mapping (category 36 → product 8432)
3. Achieve 90% code coverage

Use MCP terminal server to run pytest.
```

---

### Agent 4: DevOps Engineer

**Role:** Deploy and monitor infrastructure

**Specialization:**
- Docker deployment
- CI/CD pipelines
- Monitoring setup
- Performance optimization

**Tools:**
- `terminal` (docker commands)
- `git` (deploy scripts)
- `filesystem` (config files)

**Example Prompt:**
```
You are a DevOps engineer deploying DXBX Onboarding Bot to production.

Task: Create Docker Compose configuration for production.

Requirements:
1. Create docker-compose.prod.yml
2. Configure PostgreSQL with persistent storage
3. Setup nginx reverse proxy with SSL
4. Configure health checks

Use MCP filesystem server to create config files.
```

---

### Agent 5: Documentation Writer

**Role:** Write and maintain documentation

**Specialization:**
- API documentation
- User guides
- Architecture diagrams
- README files

**Tools:**
- `filesystem` (read/write docs)
- `git` (commit docs)
- `bitrix24` (get examples)

**Example Prompt:**
```
You are a technical writer documenting DXBX Onboarding Bot.

Task: Write documentation for product stages feature.

Requirements:
1. Document bitrix_product_service.py API
2. Create usage examples in docs/PRODUCT_STAGES.md
3. Add architecture diagram showing entityTypeId 1056

Use MCP filesystem server to write documentation.
```

---

## 🔄 WORKFLOWS

### Workflow 1: Feature Development

```
1. Developer Agent receives task
2. Reads existing code via filesystem MCP
3. Writes new feature
4. Testing Agent runs tests via terminal MCP
5. If tests pass, DevOps Agent deploys via git MCP
6. Documentation Agent updates docs via filesystem MCP
```

**MCP Sequence:**
```
filesystem.read_file → filesystem.write_file → terminal.execute → git.commit → filesystem.write_file
```

---

### Workflow 2: Bug Fix

```
1. Testing Agent detects bug via tests
2. Developer Agent reads failing test
3. Developer Agent fixes code
4. Testing Agent re-runs tests
5. DevOps Agent merges fix via git MCP
```

**MCP Sequence:**
```
terminal.execute → filesystem.read_file → filesystem.write_file → terminal.execute → git.merge_branch
```

---

### Workflow 3: Database Migration

```
1. Database Agent creates migration
2. Database Agent tests migration
3. Developer Agent updates models
4. Testing Agent tests new schema
5. DevOps Agent applies migration
```

**MCP Sequence:**
```
filesystem.write_file → database.query → filesystem.write_file → terminal.execute → database.query
```

---

## ⚙️ CONFIGURATION

### MCP Orchestrator Config

**File:** `mcp_config.json`

```json
{
  "orchestrator": {
    "name": "DXBX Onboarding Bot Orchestrator",
    "version": "1.0",
    "project_root": "e:\\Carrot1_WaitingClient"
  },
  "agents": {
    "developer": {
      "model": "claude-sonnet-4-5-20250929",
      "tools": ["filesystem", "terminal", "git"],
      "max_iterations": 10
    },
    "database": {
      "model": "claude-sonnet-4-5-20250929",
      "tools": ["database", "filesystem", "terminal"],
      "max_iterations": 5
    },
    "testing": {
      "model": "claude-sonnet-4-5-20250929",
      "tools": ["terminal", "filesystem", "telegram"],
      "max_iterations": 5
    },
    "devops": {
      "model": "claude-sonnet-4-5-20250929",
      "tools": ["terminal", "git", "filesystem"],
      "max_iterations": 5
    },
    "documentation": {
      "model": "claude-sonnet-4-5-20250929",
      "tools": ["filesystem", "git", "bitrix24"],
      "max_iterations": 3
    }
  },
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

## 📖 USAGE EXAMPLES

### Example 1: Add New Feature

**User Request:**
```
Add endpoint to get product stages for card 18518
```

**Orchestrator Actions:**
1. Assign to Developer Agent
2. Developer reads `app/services/bitrix_product_service.py`
3. Developer adds endpoint to `app/api/routes/cards.py`
4. Testing Agent runs tests
5. Documentation Agent updates docs

**MCP Calls:**
```json
{
  "steps": [
    {"agent": "developer", "tool": "filesystem.read_file", "params": {"path": "app/services/bitrix_product_service.py"}},
    {"agent": "developer", "tool": "filesystem.write_file", "params": {"path": "app/api/routes/cards.py", "content": "..."}},
    {"agent": "testing", "tool": "terminal.execute", "params": {"command": "pytest tests/test_product_service.py"}},
    {"agent": "documentation", "tool": "filesystem.write_file", "params": {"path": "docs/PRODUCT_STAGES.md", "content": "..."}}
  ]
}
```

---

### Example 2: Fix Database Issue

**User Request:**
```
Fix asyncpg connection issues on Windows
```

**Orchestrator Actions:**
1. Assign to Database Agent
2. Database Agent reads `app/database/connection.py`
3. Database Agent creates sync version with psycopg2
4. Testing Agent tests database connections
5. DevOps Agent commits changes

**MCP Calls:**
```json
{
  "steps": [
    {"agent": "database", "tool": "filesystem.read_file", "params": {"path": "app/database/connection.py"}},
    {"agent": "database", "tool": "filesystem.write_file", "params": {"path": "app/database/db_sync.py", "content": "..."}},
    {"agent": "testing", "tool": "terminal.execute", "params": {"command": "python tools/check_db_connection.py"}},
    {"agent": "devops", "tool": "git.commit", "params": {"message": "fix: Add sync database connection with psycopg2"}}
  ]
}
```

---

### Example 3: Test Bitrix24 Integration

**User Request:**
```
Test product stages retrieval for card 17900
```

**Orchestrator Actions:**
1. Assign to Testing Agent
2. Testing Agent runs test script
3. Testing Agent verifies Mercury mapping
4. Developer Agent fixes issues if found

**MCP Calls:**
```json
{
  "steps": [
    {"agent": "testing", "tool": "terminal.execute", "params": {"command": "python tools/test_card_17900.py"}},
    {"agent": "testing", "tool": "bitrix24.get_card", "params": {"card_id": 17900}},
    {"agent": "testing", "tool": "bitrix24.get_product_stages", "params": {"card_id": 17900}}
  ]
}
```

---

## 🚀 GETTING STARTED

### 1. Install MCP CLI

```bash
npm install -g @modelcontextprotocol/cli
```

### 2. Configure MCP Servers

Create `mcp_config.json` as shown above.

### 3. Start MCP Orchestrator

```bash
mcp-orchestrator --config mcp_config.json
```

### 4. Run AI Agents

```bash
mcp-agent start developer
mcp-agent start database
mcp-agent start testing
mcp-agent start devops
mcp-agent start documentation
```

---

## 📝 NOTES

1. **Security:** All MCP servers run with minimal required permissions
2. **Logging:** All agent actions are logged to `logs/mcp_orchestrator.log`
3. **Error Handling:** Agents retry failed operations up to 3 times
4. **Rate Limiting:** API calls to Bitrix24 and Telegram are rate-limited

---

**Documentation created:** 27.02.2026  
**DXBX AI Team**
