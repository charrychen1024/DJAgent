# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

DJAgent is an AI-powered risk management system built with React + FastAPI + Claude Agent SDK.

## Project Overview

- **Purpose**: AI risk management assistant for logistics/supply chain scenarios
- **Users**: Business managers (risk analysis, task dispatch) and frontline staff (task execution, feedback)
- **Architecture**: React frontend + FastAPI backend + Claude Agent SDK + MCP

## Running the Project

**Mac/Linux:**
```bash
# Backend (port 5005)
cd backend && source venv/bin/activate && unset CLAUDECODE && python -m uvicorn app_fastapi:app --reload --port 5005

# Frontend (port 5173)
cd frontend && npm run dev
```

**Windows:**
```bash
cd backend && venv\Scripts\activate && set CLAUDECODE= && python -m uvicorn app_fastapi:app --reload --port 5005 --loop auto
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

## Project Branches

- `main` - Production branch
- `feature/ui-optimization` - UI improvements (current)
- `feature/skill-based-agent` - Skill-based agent implementation
