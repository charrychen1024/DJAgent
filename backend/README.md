# DJAgent - 风险管理 AI 数字员工

**版本**: v2.3.0 | **文档**: v2.4.0 | **最后更新**: 2026-03-23

---

## 📋 目录

1. [快速开始](#快速开始)
2. [文档索引](#文档索引)
3. [项目概览](#项目概览)
4. [核心功能](#核心功能)
5. [技术栈](#技术栈)
6. [项目结构](#项目结构)
7. [API 快速参考](#api-快速参考)
8. [配置说明](#配置说明)
9. [常见问题](#常见问题)
10. [贡献指南](#贡献指南)

---

## 文档索引

本项目文档按用途分类，以下为核心文档：

### 📘 必读文档

| 文档 | 位置 | 用途 |
|------|------|------|
| **CLAUDE.md** | `./CLAUDE.md` | 🔧 Claude Code 开发指南（项目指导） |
| **README.md** | `./README.md` | 📖 项目总体说明 |
| **PRD.md** | `./docs/PRD.md` | 📋 产品需求文档 |
| **DEVELOPMENT.md** | `./docs/DEVELOPMENT.md` | 🏗️ 开发设计与架构 |

### 📌 参考文档

| 文档 | 位置 | 用途 |
|------|------|------|
| **ARCHITECTURE.md** | `./docs/ARCHITECTURE.md` | 🎯 详细架构设计 |
| **CHANGELOG.md** | `./docs/CHANGELOG.md` | 📝 版本变更日志 |
| **TODO.md** | `./docs/TODO.md` | ✅ 待办事项和进度跟踪 |

**提示**：所有文档均采用 Markdown 格式，可在任何文本编辑器或 IDE 中查看。

---

## 快速开始

### 环境要求
- **Python**: 3.9+
- **Node.js**: 14+
- **虚拟环境**: `.venv` (Python venv)

### 后端启动

```bash
cd backend

# 1. 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate      # Windows

# 2. 取消设置 CLAUDE 环境变量（重要！）
unset CLAUDE                # macOS/Linux
# 或
set CLAUDE=                 # Windows

# 3. 启动 FastAPI 服务器
python -m uvicorn app_fastapi:app --reload --host 0.0.0.0 --port 5005
```

**Windows 用户特别说明**:
由于 Windows 的 asyncio 限制，必须使用 `--loop auto` 参数:
```cmd
python -m uvicorn app_fastapi:app --loop=auto --host 0.0.0.0 --port 5005
```

### 前端启动

```bash
cd frontend
npm run dev
```

访问 http://localhost:5173

---

## 项目概览

### 产品定位
面向物流/供应链场景的企业级 AI 智能助手，帮助：
- **业务负责人**: 风险数据分析、任务分派、效果评估
- **一线人员**: 任务执行、核查指导、反馈提交

### 核心优势
- **AI 赋能**: 基于 Claude Agent SDK 的自然语言交互
- **工作流自动化**: 任务从创建→下发→反馈→完成全自动流转
- **智能决策**: Agent 自主分析数据、推荐执行人、生成总结
- **实时协作**: SSE 推送、即时通知、进度跟踪
- **精细权限**: 基于角色和地区的多层级权限控制

### 关键指标（设计目标）
- 风险识别效率提升 80%
- 人工核查成本降低 60%
- 任务完成时间缩短 50%
- 系统可用性 99%

---

## 核心功能

### 1. 用户管理
- **两种角色**: 业务负责人（Manager）和一线人员（Staff）
- **角色卡片选择**: 登录时选择身份
- **快速用户切换**: 个人中心菜单切换
- **权限隔离**: 每个角色只能看到授权的数据

### 2. 风险数据管理（业务负责人）
| 功能 | 说明 |
|------|------|
| 日度/月度 Tab | 切换查看每日明细和月度汇总数据 |
| 地区筛选 | 按用户地区自动过滤风险数据 |
| 智能搜索 | 全局搜索和字段精确搜索 |
| 数据统计 | 高/中/低风险数量统计看板 |
| 分页查看 | 支持 5/10/20/50/100 条/页 |

**数据来源**:
- 日度数据: `data/risk_data_*.csv` (10个文件)
- 月度数据: `data/risk_data_monthly_*.csv` (12个文件)
- 自动更新: 用户可上传新数据

### 3. 任务管理

#### 任务创建和下发
```
业务负责人  →  AI 对话创建任务  →  选择执行人  →  下发通知
```

**任务状态流转**:
```
已创建 → 已下发 → 反馈中 → 已完成
                 ↓
               已超时
```

#### 任务字段说明
| 字段 | 说明 | 示例 |
|------|------|------|
| task_id | 任务 ID (自动生成) | 001-20260323101500123-001 |
| creator_id | 创建人工号 | EMP_001 |
| assigned_to_id | 执行人工号 | EMP_009 |
| status | 任务状态 | 已下发 |
| feedback_deadline | 反馈截止时间 | 2026-03-24 10:00:00 |
| feedback_summary | AI 生成总结 | （完成时填充） |
| region | 所属地区 | 上海区 |

#### 超期处理
- **自动检测**: 在 get_tasks API 中自动检查是否超期
- **自动更新**: 超期自动更新状态为"已超时"
- **继续对话**: 超期后仍可对话，但提示"任务已超期"

### 4. AI 对话交互

#### Manager Agent (业务负责人)
**核心能力**:
- 风险数据分析 (分析趋势、异常识别)
- 文件解析 (CSV、Excel、PDF、Word)
- 执行人推荐 (基于能力和工作量)
- 任务创建 (自然语言指导)
- 报告生成 (数据汇总和分析)

**可用工具**: list_users, create_task, assign_task, get_task_detail, parse_csv, read_risk_data, 等18个

**使用示例**:
```
你: 帮我分析今天的风险数据，有哪些高风险
Agent: [读取风险数据] 找到 15 个高风险项目：
       - 运单异常占比 45%
       - 重量错误占比 30%
       ...建议针对异常类型创建核查任务
```

#### Staff Agent (一线人员)
**核心能力**:
- 任务推送 (接收任务通知，了解要求)
- 核查指导 (提供最佳实践，回答疑问)
- 文件验证 (检查上传内容是否符合要求)
- 反馈总结 (生成任务完成总结)
- 进度督促 (截止前提醒，超期警告)

**使用示例**:
```
Agent: 您有新任务：运单WLYD001 重量异常核查
       需要提供：1) 货物照片 2) 称重凭证 3) 核查报告
       截止时间：2026-03-24 18:00

你: 已上传照片和凭证
Agent: [检查内容] 内容符合要求。请提交核查报告
```

### 5. 文件管理
- **支持格式**: PDF、JPG、PNG、DOCX、DOC
- **大小限制**: 单文件 < 50MB
- **存储位置**: `data/uploads/{task_id}/{filename}`
- **智能解析**: 自动提取文本内容供 AI 分析

### 6. 实时通知 (SSE)
- **事件类型**: task_created（任务创建）、task_updated（任务更新）、task_completed（任务完成）
- **推送方式**: 服务端主动推送，客户端实时接收
- **自动重连**: 连接断开后自动重新连接（间隔3秒）

---

## 技术栈

### 后端
```
Framework:    FastAPI 0.115.0+
Server:       Uvicorn 0.24.0
AI SDK:       Claude Agent SDK
SDK Type:     MCP (Model Context Protocol)
Language:     Python 3.9+
Data:         CSV/JSON 文件存储
```

### 前端
```
Framework:    React 19.2.0
Build Tool:   Vite 7.3.1
Components:   React Markdown, Recharts
Styling:      CSS3
Communication: Fetch API, SSE (Server-Sent Events)
```

### 核心依赖
```
# 数据处理
pandas>=2.1.0
openpyxl>=3.1.0

# 文件解析
PyPDF2>=3.0.0
pdfplumber>=0.10.0
python-docx>=1.1.0

# HTTP 客户端
httpx>=0.25.0
requests>=2.31.0

# 环境管理
python-dotenv==1.0.0
```

---

## 项目结构

```
DJAgent-feature-backend-optimization/
│
├── backend/                          # 后端服务
│   ├── app_fastapi.py               # FastAPI 入口，14 个 API 端点
│   ├── agents/                      # Agent 核心
│   │   ├── unified_agent.py         # 统一 Agent 包装器 (464 行)
│   │   ├── config.py                # Agent 配置管理 (428 行)
│   │   ├── session_manager.py       # 会话管理 (211 行)
│   │   ├── manager_agent.py         # Manager 专用 Agent (240 行)
│   │   ├── staff_agent.py           # Staff 专用 Agent (382 行)
│   │   ├── mcp_server.py            # MCP 工具注册 (499 行，18 个工具)
│   │   ├── skill_orchestrator.py    # Skill 编排引擎 (343 行)
│   │   ├── skill_handler.py         # Skill 加载执行 (253 行)
│   │   ├── sse_events.py            # SSE 实时推送 (135 行)
│   │   ├── identity/                # Agent 身份文档
│   │   │   ├── MANAGER_AGENT.md
│   │   │   └── STAFF_AGENT.md
│   │   ├── skills/                  # 6 个业务 Skill
│   │   │   ├── risk_analyzer/       # 风险分析
│   │   │   ├── task_creator/        # 任务创建
│   │   │   ├── receiver_recommender/# 执行人推荐
│   │   │   ├── summary_generator/   # 反馈总结
│   │   │   ├── 核查_guider/         # 核查指导
│   │   │   └── hello_world/         # 演示 Skill
│   │   └── tools/                   # MCP 工具 (2,223 行)
│   │       ├── data_access.py       # CSV/JSON 读写 (379 行)
│   │       ├── data_query.py        # 数据查询 (253 行)
│   │       ├── file_ops.py          # 文件操作 (303 行)
│   │       ├── file_parser.py       # 文件解析 (295 行)
│   │       ├── task_manager.py      # 任务 CRUD (492 行)
│   │       └── tools.py             # 工具定义 (366 行)
│   │
│   ├── data/                        # 数据目录 (1MB)
│   │   ├── users.csv               # 25 个用户信息
│   │   ├── tasks.csv               # 15+ 个任务记录
│   │   ├── risk_data_*.csv         # 10 个日度风险数据
│   │   ├── risk_data_monthly_*.csv # 12 个月度风险数据
│   │   ├── feedback/               # 40+ 个反馈记录 (JSON)
│   │   ├── chats/                  # 对话历史 (JSON)
│   │   └── task_creation/          # 任务创建记录 (JSON)
│   │
│   ├── requirements.txt             # Python 依赖
│   └── .env                        # 环境配置 (需自行创建)
│
├── frontend/                        # 前端应用
│   ├── src/
│   │   ├── App.jsx                 # 主应用，包含所有组件 (2000+ 行)
│   │   │   ├── LoginPage           # 登录和角色选择
│   │   │   ├── ManagerWorkspace    # 业务负责人工作区
│   │   │   ├── StaffWorkspace      # 一线人员工作区
│   │   │   └── 其他辅助组件
│   │   ├── App.css                 # 主样式
│   │   ├── index.css               # 全局样式
│   │   └── main.jsx                # React 入口
│   │
│   ├── package.json                # NPM 依赖
│   ├── vite.config.js              # Vite 配置
│   └── index.html                  # HTML 入口
│
├── docs/                           # 文档 (精简版本)
│   ├── README.md                  # 本文件
│   ├── PRD.md                     # 产品需求文档
│   ├── ARCHITECTURE.md            # 架构设计文档
│   ├── DEVELOPMENT.md             # 开发指南
│   ├── TODO.md                    # 开发进度
│   ├── CHANGELOG.md               # 版本日志
│   └── CLAUDE.md                  # Claude Code 指导 (根目录)
│
├── .gitignore                     # Git 忽略规则
├── CLAUDE.md                      # 项目指导 (根目录)
└── README.md                      # 项目主文档 (根目录)
```

---

## API 快速参考

### 用户管理
| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/api/users` | GET | 获取用户列表 | 无 |
| `/api/users/{employee_id}` | GET | 获取用户信息 | employee_id: EMP_001 |

### 任务管理
| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/api/tasks` | GET | 获取任务列表 | employee_id, task_type (日度/月度) |
| `/api/tasks` | POST | 创建任务 | creator_id, assigned_to_id, risk_summary, feedback_deadline |
| `/api/tasks/{task_id}` | GET | 获取任务详情 | task_id |
| `/api/tasks/{task_id}` | PUT | 更新任务 | status, feedback_summary |
| `/api/tasks/{task_id}/message` | POST | 发送任务消息 | message, files |

### 风险数据
| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/api/risk-data` | GET | 列出可用文件 | 无 |
| `/api/risk-data/{filename}` | GET | 获取风险数据 | filename: risk_data_001.csv |

### AI 交互
| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/api/chat` | POST | AI 对话 | FormData: message, user_id, files |
| `/api/events/{user_id}` | GET | SSE 实时推送 | 使用 employee_id |

### 文件管理
| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/api/upload` | POST | 文件上传 | FormData: file, task_id |
| `/api/files` | GET | 文件列表 | 无 |

**详细的 API 文档**: 见 [DEVELOPMENT.md](DEVELOPMENT.md) 中的 API 参考章节

---

## 配置说明

### 后端配置 (.env)

```bash
# Claude AI 配置（必须）
ANTHROPIC_BASE_URL=https://ark.cn-beijing.volces.com/api/coding
ANTHROPIC_AUTH_TOKEN=your_api_key_here

# 其他可选配置
LOG_LEVEL=INFO
PORT=5005
```

### Agent 工具授权

在 `config.py` 中配置允许的工具（使用 `mcp__` 前缀）:

```python
allowed_tools = [
    "mcp__djagent_tools__get_current_time",
    "mcp__djagent_tools__list_users",
    "mcp__djagent_tools__create_task",
    ...
]
```

**重要**: 工具名称格式为 `mcp__{server_name}__{tool_name}`，不能省略 `mcp__` 前缀

### Thinking 模式配置

在 `config.py` 中控制是否启用 Claude 的思考模式:

```python
thinking = {
    "type": "enabled",           # enabled 或 disabled
    "budget_tokens": 20000       # 思考的最大 token 数
}
```

---

## 常见问题

### 后端问题

**Q: 无法启动后端，报错 `NotImplementedError @ asyncio/base_events.py:502`**
- **原因**: Windows 上默认使用 SelectorEventLoop，不支持子进程
- **解决**: 添加 `--loop auto` 参数或激活 `.venv` 中的 Python

**Q: UnifiedAgent 导入失败**
- **原因**: claude-agent-sdk 未安装或路径错误
- **解决**: 确认 SDK 已安装，检查 `requirements.txt` 依赖

**Q: 工具不工作，提示 "tool authorization required"**
- **原因**: 工具未在 `allowed_tools` 中声明
- **解决**:
  1. 检查工具名称是否带 `mcp__` 前缀
  2. 确保工具名称拼写正确
  3. 检查 config.py 中的工具列表

**Q: SSE 连接频繁断开**
- **原因**: 网络问题或事件发送失败
- **解决**:
  1. 检查后端 sse_events.py 中的推送逻辑
  2. 查看浏览器控制台的 SSE 连接日志
  3. 前端自动重连（间隔 3 秒）

### 前端问题

**Q: API 返回 404**
- **原因**: 前端调用的端点与后端实现不匹配
- **解决**: 检查 App.jsx 中的 API 调用，对照本文档的 API 表

**Q: 文件上传失败**
- **原因**: 前端未使用 FormData 格式
- **解决**: 确保前端发送的是 FormData，后端正确使用 `File()` 接收

**Q: 登录后显示空白页面**
- **原因**: 会话初始化失败或 API 调用异常
- **解决**:
  1. 打开浏览器开发者工具（F12）
  2. 查看 Network 选项卡中的 API 调用是否有错误
  3. 检查后端日志是否有异常

### 数据问题

**Q: 风险数据显示不出来**
- **原因**: CSV 文件不存在或格式不对
- **解决**:
  1. 检查 `data/risk_data_*.csv` 文件是否存在
  2. 确保 CSV 文件包含 `region` 字段
  3. 检查 CSV 编码是否为 UTF-8

**Q: 任务创建失败**
- **原因**: 执行人不存在或权限不足
- **解决**:
  1. 确保执行人的 employee_id 在 users.csv 中存在
  2. 检查创建人是否有权限创建任务
  3. 查看后端日志中的具体错误

---

## 贡献指南

### 代码规范
- **Python**: PEP 8，使用 black 格式化
- **JavaScript**: ESLint 配置，使用 Prettier 格式化
- **提交**: 清晰的提交信息，关联相关的 issue

### 开发流程
1. 创建 feature 分支: `git checkout -b feature/xxx`
2. 完成开发和测试
3. 提交 Pull Request
4. 代码审查和合并

### 如何扩展
- **新增 Skill**: 见 [DEVELOPMENT.md](DEVELOPMENT.md) 中的"如何添加 Skill"
- **新增 Tool**: 见 [DEVELOPMENT.md](DEVELOPMENT.md) 中的"如何添加 Tool"
- **新增 Agent**: 见 [DEVELOPMENT.md](DEVELOPMENT.md) 中的"如何扩展 Agent"

### 测试
```bash
# 运行测试
pytest backend/

# 查看覆盖率
pytest --cov=backend/

# 前端测试
npm test
```

---

## 相关文档

- **[PRD.md](PRD.md)** - 完整的产品需求和设计文档
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 架构设计和实现细节
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - 开发指南和如何扩展
- **[TODO.md](TODO.md)** - 开发进度和待做事项
- **[CHANGELOG.md](CHANGELOG.md)** - 版本历史和更新记录

---

**最后更新**: 2026-03-23
**文档版本**: v2.4.0
**代码版本**: v2.3.0
**维护者**: DJAgent Team
**许可证**: MIT
