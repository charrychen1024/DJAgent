# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DJAgent is a risk management AI assistant system built with React + FastAPI + Claude Agent SDK. It features an AI agent that can help business managers with risk data analysis, task management, and staff coordination.

## Commands

### Backend (FastAPI)
```bash
cd backend
source venv/bin/activate
unset CLAUDECODE  # Required to avoid nested Claude Code session error
python -m uvicorn app_fastapi:app --reload --host 0.0.0.0 --port 5005
```

### Frontend (React + Vite)
```bash
cd frontend
npm run dev
```

## Architecture

### Backend Structure
```
backend/
├── app_fastapi.py          # FastAPI entry point, REST API endpoints
├── agents/
│   ├── unified_agent.py    # Core Agent class (Claude SDK wrapper)
│   ├── config.py           # AgentConfig - SDK configuration
│   ├── mcp_server.py       # MCP server with tools
│   ├── session_manager.py  # Session management, Agent lifecycle
│   ├── manager_agent.py    # Legacy Manager Agent (kept for compatibility)
│   ├── staff_agent.py      # Legacy Staff Agent
│   └── skills/             # Skill modules (dynamically loaded)
└── requirements.txt
```

### Agent Flow
1. Frontend sends POST to `/api/chat` with `message`, `user_id`, `username`
2. `session_manager.get_or_create_manager_agent()` creates/reuses UnifiedAgent
3. `UnifiedAgent.chat()` builds prompt and calls Claude SDK
4. SDK handles ReAct loop, tool execution via MCP server
5. Response extracted from SDK message blocks (TextBlock, ThinkingBlock)

### Agent Modes
- **Manager**: Business manager mode, uses MCP tools
- **Staff**: Frontline operator mode, uses Skills

## Key Configuration

### Thinking Configuration (config.py)
```python
"thinking": {"type": "enabled", "budget_tokens": 20000}
```

### Tool Authorization
Tools must be explicitly authorized via `allowed_tools` list in config.py. Without this, agent will report "tool authorization required".

## Important Notes

- The backend MUST be started with `unset CLAUDECODE` to avoid nested Claude Code session errors
- API runs on port 5005, frontend on port 5173/5174
- Frontend API_BASE in App.jsx must match backend port
- Agent sessions are cached by user_id in SessionManager - refresh page to apply config changes

# 复杂问题排查与修复
- 当用户没有跟你说全自动修复时，不允许未经用户确认直接修改源代码
- 复杂的代码问题，多次提问到的问题，多次修改但没有效果的问题，需要先仔细排查代码，从全局到局部层层分析，给出原因和解释
