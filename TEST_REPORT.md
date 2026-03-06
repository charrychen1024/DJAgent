# DJAgent 项目测试报告

**测试日期**: 2026-03-06  
**测试范围**: 后端API、Agent模块、前端组件、数据文件  
**测试环境**: 本地开发环境

---

## 一、项目概览

| 项目 | 信息 |
|------|------|
| 后端框架 | FastAPI |
| 前端框架 | React + Vite |
| 主要功能 | 风控智能助手，支持业务负责人和一线人员协作 |
| 后端入口 | `backend/app_fastapi.py` |
| 前端入口 | `frontend/src/App.jsx` |

---

## 二、发现的Bug和问题

### 🔴 严重问题（功能缺失/阻塞）

#### 1. 后端API接口缺失
**位置**: `backend/app_fastapi.py`

**问题描述**:
前端调用的多个接口在后端中未实现，导致功能无法正常工作。

**缺失接口列表**:
- ❌ `GET /api/risk-data` - 前端第87行调用，用于获取所有风险数据
- ❌ `GET /api/risk-data/{filename}` - 前端第87行调用，用于获取单个风险数据文件
- ❌ `GET /api/tasks/{task_id}/creation-history` - 前端第138行调用，用于获取任务创建历史
- ❌ `GET /api/feedback/{task_id}` - 前端第150行调用，用于获取任务反馈信息
- ❌ `POST /api/tasks/{task_id}/upload-file` - 前端第195、551行调用，用于上传文件

**影响**: 
- 前端风险数据加载失败
- 任务详情无法查看
- 文件上传功能不可用

**代码位置**: 
- `frontend/src/App.jsx:87-96` (fetchAllRiskData)
- `frontend/src/App.jsx:134-158` (handleTaskClick)
- `frontend/src/App.jsx:183-203, 540-557` (handleFileUpload)

---

#### 2. 聊天消息未保存
**位置**: `backend/app_fastapi.py:206-241`

**问题描述**:
`POST /api/tasks/{task_id}/message` 接口处理消息后直接返回，但未将消息保存到 `data/feedback/{task_id}.json` 文件中。

**当前代码**:
```python
@app.post("/api/tasks/{task_id}/message")
async def send_message(task_id: str, request: Request):
    # ... 处理消息 ...
    return {
        'user_message': user_message,
        'agent_reply': agent_reply
    }
    # ❌ 未保存到文件
```

**影响**:
- 刷新页面后聊天消息丢失
- `GET /api/tasks/{task_id}/chat-history` 无法返回历史消息
- 对话历史无法持久化

---

#### 3. 聊天历史接口参数不匹配
**位置**: `backend/app_fastapi.py:168`

**问题描述**:
接口定义为路径参数，但前端通过Query参数调用。

**当前代码**:
```python
async def get_chat_history(task_id: str, user_id: str, username: str):
```

**前端调用**:
```javascript
const historyRes = await fetch(`${API_BASE}/tasks/${pendingTask.task_id}/chat-history`)
// user_id 和 username 未传递
```

**影响**: 
- 接口调用失败
- 无法正确获取聊天历史

---

### 🟡 中等问题（功能缺陷/隐患）

#### 4. 会话管理器异步处理错误
**位置**: `backend/agents/session_manager.py:45, 75`

**问题描述**:
在已有事件循环中调用 `asyncio.run()`，会导致运行时错误。

**当前代码**:
```python
asyncio.run(agent.__aenter__())  # ❌ 错误：在已有事件循环中调用
```

**正确做法**:
```python
await agent.__aenter__()  # ✅ 直接await
```

**影响**: 
- Agent会话无法创建
- 服务启动时可能崩溃

**错误信息**:
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

---

#### 5. 缺少依赖管理
**位置**: `backend/requirements.txt:10`

**问题描述**:
`claude-agent-sdk` 依赖被注释掉，但代码中实际使用了该依赖。

**当前状态**:
```python
# Agent SDK - 暂时注释掉，需要手动安装或替换
# claude-agent-sdk
```

**实际导入**:
- `backend/agents/manager_agent.py:11-18`
- `backend/agents/staff_agent.py:12-19`

**影响**: 
- ManagerAgent 和 StaffAgent 无法启动
- AI对话功能不可用

---

#### 6. Agent工具未注册
**位置**: `backend/agents/manager_agent.py:71-83`

**问题描述**:
虽然在 `tools.py` 中定义了 `AGENT_TOOLS` 列表，但在创建 Agent 时未传入。

**当前代码**:
```python
def build_manager_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        env={...},
        system_prompt=MANAGER_SYSTEM_PROMPT,
        permission_mode="acceptEdits",
        max_turns=15,
        thinking={"type": "disabled"}
    )
    # ❌ 未传入 tools 参数
```

**可用工具**:
- parse_csv, parse_excel, parse_pdf, parse_word
- read_risk_data, list_users, get_task_status, get_task_detail

**影响**: 
- Agent无法调用文档解析工具
- Agent无法查询任务状态
- Agent功能受限

---

#### 7. 缺少用户身份验证
**位置**: 所有API接口

**问题描述**:
所有API接口都没有验证 `user_id` 是否有效，存在数据安全隐患。

**示例**:
```python
@app.get("/api/tasks")
async def get_tasks(user_id: Optional[str] = None):
    tasks = read_csv_file('tasks.csv')
    # ❌ 未验证 user_id 是否存在于 users.csv
    if user_id:
        # 直接返回该用户相关数据
```

**影响**: 
- 任何人可以通过修改 user_id 访问他人数据
- 数据安全性不足

---

#### 8. 前端全选逻辑错误
**位置**: `frontend/src/App.jsx:256`

**问题描述**:
全选复选框只在当前页生效，但用户期望全选所有数据。

**当前代码**:
```jsx
checked={selectedRows.length === currentPageData.length && currentPageData.length > 0}
```

**期望行为**:
- 点击全选应该选中所有数据（所有页）
- 当前实现只在当前页有效

**影响**: 
- 用户体验不佳
- 全选功能与预期不符

---

#### 9. 数据不一致
**位置**: `data/tasks.csv` vs `data/users.csv`

**问题描述**:
任务记录中的创建人名称与用户表中的数据不匹配。

**数据对比**:
| tasks.csv | users.csv |
|-----------|-----------|
| 创建人: 李经理 | 用户名: 王经理 |
| 创建人ID: 001 | 用户ID: 001 (王经理) |

**影响**: 
- 用户信息显示错误
- 数据可信度降低

---

### 🟢 轻微问题（代码质量/规范）

#### 10. 未使用的导入
**位置**: `backend/agents/manager_agent.py:16-18`

**问题代码**:
```python
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,        # ❌ 未使用
    ResultMessage,       # ❌ 未使用
)
```

**建议**: 移除未使用的导入

---

#### 11. 缺少错误处理
**位置**: `backend/app_fastapi.py:168-204`

**问题描述**:
`get_chat_history` 接口中 Agent 初始化失败的错误处理不够详细。

**当前代码**:
```python
except Exception as e:
    logger logger.error(f"[ERROR] Agent初始化失败: {str(e)}")
    return [{"message": "任务加载失败", "sender": "Agent"}]
```

**建议**: 
- 区分不同类型的错误
- 返回更详细的错误信息

---

#### 12. CORS配置限制
**位置**: `backend/app_fastapi.py:27`

**问题描述**:
只允许 `localhost:5173` 和 `127.0.0.1:5173`，不支持其他域名或部署环境。

**当前配置**:
```python
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
```

**建议**: 
- 支持环境变量配置
- 生产环境使用具体域名
- 开发环境使用通配符

---

#### 13. 缺少目录存在性检查
**位置**: `backend/agents/staff_agent.py:196`

**问题描述**:
虽然代码中有 `mkdir` 操作，但在读取反馈文件前未检查目录是否存在。

**建议**: 在文件操作前确保目录存在

---

#### 14. Agent模型配置不一致
**位置**: `.env` vs `manager_agent.py:75`

**问题描述**:
环境变量配置与代码中的默认值不一致。

**对比**:
- `.env`: `ANTHROPIC_MODEL=MiniMax-M2.5`
- 代码默认值: `https://ark.cn-beijing.volces.com/api/coding`

**建议**: 统一配置来源

---

## 三、测试覆盖范围

### 已测试模块
- ✅ 后端 FastAPI 接口
- ✅ ManagerAgent 模块
- ✅ StaffAgent 模块
- ✅ SessionManager 模块
- ✅ Tools 工具模块
- ✅ 前端 React 组件
- ✅ 数据文件（CSV、JSON）

### 未测试模块
- ⚠️ 集成测试（前后端联调）
- ⚠️ 性能测试
- ⚠️ 安全测试

---

## 四、统计摘要

| 问题等级 | 数量 | 占比 |
|---------|------|------|
| 🔴 严重 | 3 | 21.4% |
| 🟡 中等 | 6 | 42.9% |
| 🟢 轻微 | 5 | 35.7% |
| **总计** | **14** | **100%** |

---

## 五、测试结论

**总体评价**: ⚠️ 项目存在多个严重功能缺失，需要优先修复后才能正常使用。

**关键问题**:
1. 5个后端API接口缺失（阻断前端功能）
2. 聊天消息无法保存（数据持久化问题）
3. 会话管理器异步错误（Agent无法启动）
4. 依赖包未正确配置

**建议行动**:
1. 立即修复P0级别问题（API缺失、消息保存、会话管理）
2. 尽快修复P1级别问题（依赖、工具注册、身份验证）
3. 后续优化P2级别问题（代码质量、配置优化）

**下一步**: 查看修复计划文档（FIX_PLAN.md）
