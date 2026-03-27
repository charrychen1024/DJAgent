# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

DJAgent is an AI-powered risk management system built with React + FastAPI + Claude Agent SDK.

## Project Overview

- **Purpose**: AI risk management assistant for logistics/supply chain scenarios
- **Users**: Business managers (risk analysis, task dispatch) and frontline staff (task execution, feedback)
- **Architecture**: React frontend + FastAPI backend + Claude Agent SDK + MCP

## Running the Project

**重要：必须先激活虚拟环境**

```bash
# Backend (port 5005)
cd backend
source .venv/bin/activate  # 激活虚拟环境（关键！）
unset CLAUDE  # 重要：必须取消设置 CLAUDE 环境变量，否则 Claude Agent SDK 无法正常工作
python -m uvicorn app_fastapi:app --host 0.0.0.0 --port 5005
# windows 下运行：
python -m uvicorn app_fastapi:app --loop=auto --host 0.0.0.0 --port 5005

# Frontend (port 5173)
cd frontend
npm run dev
```

## Architecture

```
Frontend (React + Vite)
    │
    ▼ HTTP/WebSocket
Backend (FastAPI)
    │
    ├─► SessionManager (per user_id cache)
    │         │
    │         ▼
    │    UnifiedAgent (Claude SDK wrapper)
    │         │
    │         ▼
    │    MCP Server (tool registry)
    │         │
    │         ▼
    │    Skills (task-specific handlers)
    │
    └─► Data Layer (JSON/CSV files)
```

## Key Backend Files

- `app_fastapi.py` - All API endpoints (23KB)
- `agents/unified_agent.py` - Claude SDK wrapper, ReAct loop
- `agents/session_manager.py` - Per user_id session caching
- `agents/mcp_server.py` - Tool registration & execution
- `agents/config.py` - SDK config (model, tools allowed, thinking mode)
- `agents/manager_agent.py` - Business manager agent
- `agents/staff_agent.py` - Frontline staff agent
- `agents/skill_handler.py` - Skill loading & execution
- `agents/skills/` - Task-specific skill modules

## Key API Endpoints

- `POST /api/chat` - Agent对话 (FormData with message, user_id, files)
- `GET /api/users` - 用户列表
- `GET /api/tasks` - 任务列表
- `GET /api/risk-data/{filename}` - 风险数据
- `GET /api/events/{user_id}` - SSE实时推送
- `POST /api/tasks/{task_id}/message` - 任务对话

## Core Principles

1. **Tool Authorization** - Declare tools in `config.py` `allowed_tools`, otherwise "tool authorization required"
2. **Session by user_id** - Sessions cached per user_id, refresh page resets
3. **File Upload** - Backend: `UploadFile = File()`, Frontend: `FormData`
4. **ThinkingBlock Access** - Use `getattr(block, 'input', None)`

## Data Storage

- Users: `data/users.csv`
- Tasks: `data/tasks.csv`
- Risk Data: `data/risk_data_*.csv`, `data/risk_data_monthly_*.csv`
- Feedback: `data/feedback/{task_id}.json`
- Uploads: `data/uploads/{task_id}/`

## Important Patterns

- Manager (Web): Three-column layout, risk data table, task list, chat area, detail panel
- Staff (Mobile): Phone simulator container, WeChat-style chat bubbles, SSE task notifications
- Tab switching: Daily/Monthly risk data views
- Region filtering: HQ users can switch regions, local users see only their region

## Debugging

- Check `config.py` `allowed_tools` if tools don't work
- Refresh page if session not taking effect
- Use `getattr(block, 'input', None)` to safely access ThinkingBlock
- Complex issues: Analyze from global to local, explain root cause before fixing

## CSS 常见陷阱（经验教训）

### 问题：短文本消息换行
**症状**："正在思考"、"收到"等2-3字短文本强制换行成多行，而长文本只有2-3行

**根本原因**：
1. `word-break: break-word` + `overflow-wrap: break-word` 导致字符级别强行换行
2. `max-width: 80%` 相对于宽度过小的父容器

**解决方案**：
```css
/* ❌ 错误 - 字符级别断行 */
word-break: break-word;
overflow-wrap: break-word;

/* ✅ 正确 - 仅在单词空格处换行 */
word-wrap: break-word;
```

关键改动（ChatMessage.css）：
```css
/* 1. 确保容器宽度正确传递 */
.chat-message {
  width: 100%;  /* 占满父容器 */
}

.message-body {
  width: 100%;  /* 让max-width正确计算 */
  min-width: 0;  /* 允许flex收缩 */
}

/* 2. 使用fit-content + max-width组合 */
.message-content {
  box-sizing: border-box;  /* padding计入width */
  width: fit-content;      /* 根据内容宽度 */
  max-width: 80%;          /* 不超过容器80% */
  word-wrap: break-word;   /* 仅在空格处换行 */
  /* ❌ 删除word-break和overflow-wrap */
}

/* 3. 删除所有冲突的word-break规则 */
.text-content {
  /* ❌ 删除 word-break: break-word; */
  word-wrap: break-word;
}
```

**调试技巧**：
- 用DevTools检查computed style中的word-break值
- 检查是否有多层CSS定义冲突（特别是App.css和ChatMessage.css）
- 记住：`word-break: break-word` 是CSS 3规范中最不推荐的属性，避免使用
- 使用`max-width: 80%`而不是`max-width: 80vw`（vw会导致气泡充满屏幕）

