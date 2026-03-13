# DJAgent - 风险管理系统

企业级风险管理 AI 助手，基于 React + FastAPI + Claude Agent SDK 构建。

## 快速启动

```bash
# 后端
cd backend
source venv/bin/activate
unset CLAUDECODE  # 避免嵌套 Claude Code 会话错误
python -m uvicorn app_fastapi:app --reload --host 0.0.0.0 --port 5005

# 前端
cd frontend
npm run dev
```

访问 http://localhost:5173

## 核心功能

- **AI 智能助手**：基于 Claude SDK 的自然语言交互
- **任务管理**：任务下发、接收、执行、反馈闭环
- **风险看板**：Web 端可视化风险数据展示
- **IM 集成**：微信风格移动端界面
- **实时推送**：SSE 消息推送，状态实时更新

## 技术栈

- 前端：React + Vite + SSE
- 后端：FastAPI + Claude Agent SDK + MCP
- 数据：JSON 文件存储

## 项目结构

```
backend/
├── app_fastapi.py      # FastAPI 入口，所有 API 接口
├── agents/
│   ├── unified_agent.py   # 统一智能体，封装 Claude SDK
│   ├── config.py         # SDK 配置（模型、工具授权、思考模式）
│   ├── mcp_server.py     # MCP 服务器，注册工具
│   ├── session_manager.py # 会话管理，按 user_id 缓存智能体
│   └── skills/           # 技能模块（Staff 模式使用）
frontend/
└── src/
    ├── App.jsx       # 前端入口，路由和状态管理
    └── components/   # UI 组件
```

## 核心概念

### 智能体模式
- **Manager 模式**：业务经理使用 MCP 工具，可查询风险数据、下发任务
- **Staff 模式**：一线员工使用 Skills，执行具体操作

### API 接口
- `POST /api/chat` - 智能体对话
- `GET /api/tasks` - 获取任务列表
- `POST /api/tasks` - 创建任务
- `GET /api/risks` - 查询风险数据
- `POST /api/upload` - 文件上传

### 数据流
1. 前端 POST /api/chat -> SessionManager 获取/创建 UnifiedAgent
2. UnifiedAgent 调用 Claude SDK，SDK 执行 ReAct 循环
3. MCP Server 处理工具调用，返回结果
4. 响应通过 SSE 实时推送到前端

## 配置要点

- 后端端口：5005，前端端口：5173
- 工具需在 `config.py` 的 `allowed_tools` 中授权，否则报"tool authorization required"
- 智能体对话记录按 user_id 缓存，刷新页面重置会话
- Thinking 模式配置：`"thinking": {"type": "enabled", "budget_tokens": 20000}`

## 常见问题

- **工具不工作**：检查 config.py 的 allowed_tools 列表
- **会话不生效**：刷新页面，SessionManager 按 user_id 缓存
- **文件上传失败**：前端用 FormData，后端用 `UploadFile = File()`
- **Windows 无法启动**：添加 `--loop auto` 参数
  ```cmd
  python -m uvicorn app_fastapi:app --reload --host 0.0.0.0 --port 5005 --loop auto
  ```
