# DJAgent - 风险管理系统

React + FastAPI + Claude Agent SDK 构建的 AI 风险管理助手。

## 启动命令

**Mac/Linux:**
```bash
cd backend && source venv/bin/activate && unset CLAUDECODE && python -m uvicorn app_fastapi:app --reload --port 5005
cd frontend && npm run dev
```

**Windows:**
```cmd
cd backend && venv\Scripts\activate && set CLAUDECODE= && python -m uvicorn app_fastapi:app --reload --port 5005 --loop auto
```

## 核心原则

1. **工具必须授权** - 在 `config.py` 的 `allowed_tools` 中显式声明，否则报 "tool authorization required"
2. **会话按 user_id 缓存** - 刷新页面重置会话
3. **文件上传** - 后端 `UploadFile = File()`，前端用 `FormData`
4. **ThinkingBlock 安全访问** - 使用 `getattr(block, 'input', None)`

## 排查原则

- 未经用户确认不直接修改源代码
- 复杂问题：从全局到局部，层层分析，给出原因和解释后再修复
