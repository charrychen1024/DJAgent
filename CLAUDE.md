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

## Project Branches

- `main` - Production branch
- `feature/ui-optimization` - UI improvements (current)
- `feature/skill-based-agent` - Skill-based agent implementation

## 任务自动通知方案（经验总结）

### 问题背景
Manager 创建任务后，需要自动通知 Staff（一线人员）有新任务需要核查。

### 问题1：Staff 收不到消息
**原因**：原方案依赖前端 SSE 连接推送消息，但 SSE 连接不稳定，导致消息无法送达。

**解决方案**：后端自动触发
1. Manager 创建任务时，在 `mcp_server.py` 的 `tool_create_task` 函数中
2. 任务创建成功后，自动获取 StaffAgent
3. 调用 `staff_agent.notify_new_task()` 发送引导消息
4. 推送 SSE 事件通知前端刷新

**关键代码** (`backend/agents/mcp_server.py`):
```python
if result.get("success"):
    task_id = result.get("task_id")
    assigned_to_id = task_info.get("assigned_to_id")
    assigned_to_name = task_info.get("assigned_to_name")

    if assigned_to_id and assigned_to_name:
        from .session_manager import get_or_create_staff_agent
        staff_agent = await get_or_create_staff_agent(assigned_to_id, assigned_to_name)
        notify_result = await staff_agent.notify_new_task(task_id, task_info)

        # 推送 SSE 事件通知前端
        if SSE_AVAILABLE:
            await sse_manager.publish_to_staff(
                assigned_to_id,
                "task_message_received",
                {"task_id": task_id, "task_info": task_info, "message": notify_result.get("message", "")}
            )
```

### 问题2：前端 SSE 连接频繁断开
**原因**：
1. Uvicorn 热重载时断开所有连接
2. 前端 useEffect 重新执行导致重新连接

**解决方案**：前端添加自动重连机制
```javascript
eventSource.onerror = (err) => {
  eventSource.close()
  setTimeout(() => {
    const newSource = new EventSource(`${API_BASE}/events/${user_id}`)
  }, 3000)
}
```

### 问题3：组件缺少函数定义
**原因**：StaffWorkspace 组件没有自己的 `fetchTasks` 函数

**解决方案**：在 StaffWorkspace 组件中添加 `fetchTasks` 函数和 `tasks` 状态

### SSE 推送事件类型
- `task_created`: Manager 创建新任务
- `new_task`: 有新任务分配给 Staff（原始事件）
- `task_message_received`: StaffAgent 自动发送消息后推送（新增）
- `task_completed`: 任务反馈完成
