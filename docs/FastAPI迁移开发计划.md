# FastAPI 架构迁移开发计划

## 背景

当前项目使用 Flask 框架，但存在以下问题：
1. Agent SDK 是异步的，Flask 需要用 `asyncio.run()` 包装，效率低
2. 并发性能有限
3. 会话管理复杂

## 迁移目标

将后端从 Flask 迁移到 FastAPI，充分发挥异步优势。

## 迁移范围

| 模块 | 当前 | 目标 |
|------|------|------|
| 框架 | Flask | FastAPI |
| 路由 | @app.route | @app.get/post |
| 会话管理 | asyncio.run() | 直接await |
| API文档 | 无 | 自动Swagger |

## 详细改动

### 1. 依赖更新
```python
# 旧
from flask import Flask, request, jsonify

# 新
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
```

### 2. 路由改造
```python
# 旧 (Flask)
@app.route('/api/chat', methods=['POST'])
def chat():
    message = request.json.get('message')
    return jsonify({'message': 'ok'})

# 新 (FastAPI)
@app.post('/api/chat')
async def chat(request: Request):
    data = await request.json()
    message = data.get('message')
    return {'message': 'ok'}
```

### 3. Agent调用改造
```python
# 旧 (Flask + asyncio.run)
def chat():
    async def get_response():
        return await agent.chat(message)
    response = asyncio.run(get_response())

# 新 (FastAPI)
@app.post('/api/chat')
async def chat():
    response = await agent.chat(message)  # 直接await
```

### 4. Session管理
- 保持现有的 session_manager.py
- 直接在 async 函数中使用

## 关键文件改动清单

| 文件 | 改动 |
|------|------|
| `backend/app.py` | 重写为 FastAPI |
| `backend/requirements.txt` | 更新依赖 |
| `backend/agents/session_manager.py` | 无需改动 |
| `backend/agents/staff_agent.py` | 无需改动 |
| `backend/agents/manager_agent.py` | 无需改动 |

## 开发步骤

### Step 1: 创建FastAPI基础结构
- 安装依赖
- 创建 app.py 骨架
- 测试健康检查接口

### Step 2: 迁移用户接口
- GET /api/users
- GET /api/users/{user_id}

### Step 3: 迁移任务接口
- GET /api/tasks
- POST /api/tasks

### Step 4: 迁移Agent接口（重点）
- POST /api/chat
- GET /api/tasks/{task_id}/chat-history
- POST /api/tasks/{task_id}/message

### Step 5: 测试验证
- 测试Agent真实回复
- 测试会话隔离
- 测试并发性能

## 待审核项

1. 路由设计是否合理？
2. 错误处理策略？
3. 会话超时策略？
