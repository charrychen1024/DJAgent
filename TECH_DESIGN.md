# DJAgent 开发设计文档 (TECH_DESIGN)

**版本**: v1.0.0  
**创建日期**: 2026-03-06  
**最后更新**: 2026-03-06

---

## 一、技术栈

### 1.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主要开发语言 |
| FastAPI | 0.104.1 | Web框架 |
| Uvicorn | 0.24.0 | ASGI服务器 |
| Python-multipart | 0.0.6 | 文件上传支持 |
| python-dotenv | 1.0.0 | 环境变量管理 |
| Pandas | 2.1.3 | 数据处理 |
| openpyxl | 3.1.2 | Excel处理 |
| PyPDF2 | 3.0.1 | PDF解析 |
| pdfplumber | 0.10.0 | PDF高级解析 |
| python-docx | 1.1.0 | Word解析 |
| httpx | 0.25.0 | HTTP客户端 |
| requests | 2.31.0 | HTTP客户端 |
| claude-agent-sdk | *可选* | AI Agent SDK |

### 1.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.2.0 | UI框架 |
| React DOM | 19.2.0 | React DOM |
| Vite | 7.3.1 | 构建工具 |
| @vitejs/plugin-react | 5.1.1 | React插件 |
| ESLint | 9.39.1 | 代码检查 |
| @types/react | 19.2.7 | TypeScript类型 |

### 1.3 开发工具

| 工具 | 用途 |
|------|------|
| VS Code | IDE |
| Git | 版本控制 |
| Postman | API测试 |
| Chrome DevTools | 调试 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                          用户界面层                         │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  业务负责人工作区   │        │  一线人员工作区(IM)  │          │
│  │  React App       │        │  React App       │          │
│  └────────┬─────────┘        └────────┬─────────┘          │
└───────────┼──────────────────────────┼────────────────────┘
            │                          │
            │ REST API / WebSocket     │
            ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        API网关层                           │
│                    FastAPI Application                     │
│  ┌──────────────────────────────────────────────────┐      │
│  │  - CORS中间件                                    │      │
│  │  - 路由管理                                      │      │
│  │  - 请求验证                                      │      │
│  │  - 错误处理                                      │      │
│  └──────────┬───────────────────────────────────────┘      │
└─────────────┼──────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                        业务逻辑层                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ ManagerAgent │  │ StaffAgent   │  │ SessionMgr   │  │
│  │ (业务负责人)   │  │  (一线人员)    │  │ (会话管理)     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            ▼                               │
│                   ┌──────────────┐                         │
│                   │  Tools      │                         │
│                   │  (工具函数)    │                         │
│                   └──────┬───────┘                         │
└──────────────────────────┼─────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                        数据访问层                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  CSV Reader  │  │  CSV Writer  │  │  Auth        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────┬───────────────────────┬─────────────────────┘
              │                       │
              ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                        数据存储层                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  users.csv   │  │  tasks.csv   │  │  risk_data*  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  feedback/   │  │  uploads/    │                     │
│  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  Claude API   │
                  │  (AI服务)      │
                  └────────────────┘
```

### 2.2 目录结构

```
DJAgent/
├── backend/                    # 后端代码
│   ├── agents/                 # Agent模块
│   │   ├── __init__.py
│   │   ├── manager_agent.py    # 业务负责人Agent
│   │   ├── staff_agent.py      # 一线人员Agent
│   │   ├── session_manager.py  # 会话管理
│   │   └── tools.py           # 工具函数
│   ├── auth.py                 # 身份认证
│   ├── app_fastapi.py          # 主应用
│   ├── app_simple.py           # 简化版（无SDK）
│   ├── requirements.txt        # Python依赖
│   └── venv/                   # 虚拟环境
├── frontend/                   # 前端代码
│   ├── public/                 # 静态资源
│   ├── src/                    # 源代码
│   │   ├── App.jsx             # 主组件
│   │   ├── App.css             # 样式
│   │   └── main.jsx            # 入口
│   ├── index.html              # HTML模板
│   ├── package.json            # 项目配置
│   └── vite.config.js          # Vite配置
├── data/                       # 数据目录
│   ├── users.csv               # 用户数据
│   ├── tasks.csv               # 任务数据
│   ├── risk_data_*.csv         # 风险数据
│   ├── feedback/               # 反馈数据
│   │   └── *.json             # 任务反馈
│   └── uploads/                # 上传文件
│       └── {task_id}/          # 任务文件夹
│           └── *.pdf/jpg/...
├── docs/                       # 文档目录
│   ├── PRD.md                  # 产品需求文档
│   ├── TECH_DESIGN.md          # 开发设计文档（本文件）
│   ├── TEST_REPORT.md          # 测试报告
│   ├── FIX_PLAN.md             # 修复计划
│   └── FIX_SUMMARY.md          # 修复总结
├── .env                        # 环境变量
├── .gitignore                  # Git忽略
└── README.md                   # 项目说明
```

---

## 三、数据库设计

### 3.1 存储方案

采用 **CSV文件存储** + **JSON文件存储** 的混合方案：

- **CSV**: 结构化数据（用户、任务、风险数据）
- **JSON**: 半结构化数据（反馈、聊天历史记录）
- **文件系统**: 二进制数据（上传文件）

### 3.2 数据模型

#### 3.2.1 用户表 (users.csv)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| user_id | string | 用户ID（主键） | 001 |
| username | string | 用户名 | 王经理 |
| role | enum | 角色：业务负责人/普通分析人员/一线操作人员 | 业务负责人 |
| department | string | 部门 | 风控部 |
| employee_id | string | 员工号 | EMP_001 |

#### 3.2.2 任务表 (tasks.csv)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| task_id | string | 任务ID（主键） | TASK_001 |
| creator_id | string | 创建人ID | 001 |
| creator_name | string | 创建人名称 | 王经理 |
| assigned_to_id | string | 执行人ID | 016 |
| assigned_to_name | string | 执行人名称 | 李伟员工 |
| status | enum | 状态：已创建/已下发/反馈中/反馈完成/已超期 | 反馈完成 |
| created_time | datetime | 创建时间 | 2026-03-01 10:00 |
| risk_summary | string | 风险简述 | 超时派送风险核查 |
| risk_data_url | string | 风险数据文件路径 | data/risk_data_002.csv |
| suggested_receiver_id | string | 推荐执行人ID | 016 |
| confirmed_receiver_id | string | 确认执行人ID | 016 |
| completed_time | datetime | 完成时间 | 2026-03-01 16:00 |

#### 3.2.3 风险数据表 (risk_data_*.csv)

| 字段 | 类型 | 说明 |
|------|------|------|
| 运单号 | string | 运单唯一标识 |
| 发货地 | string | 发货地址 |
| 收货地 | string | 收货地址 |
| 揽收人 | string | 揽收人姓名 |
| 揽收人ID | string | 揽收人ID |
| 客户名称 | string | 客户公司名称 |
| 供应商名称 | string | 供应商名称 |
| 货物类型 | string | 货物类型 |
| 产品类型 | string | 产品类型 |
| 重量 | string | 货物重量 |
| 体积 | string | 货物体积 |
| 运费金额 | string | 运费 |
| 结算金额 | string | 结算金额 |
| 发货时间 | datetime | 发货时间 |
| 揽收时间 | datetime | 揽收时间 |
| 派件时间 | datetime | 派件时间 |
| 签收时间 | datetime | 签收时间 |
| 运单状态 | string | 运单状态 |
| 对账人 | string | 对账人 |
| 公里数 | int | 运输公里数 |
| 发货网点 | string | 发货网点 |
| 收货网点 | string | 收货网点 |
| 异常类型 | string | 异常类型 |
| 风险等级 | enum | 风险等级：高/中/低 |

#### 3.2.4 反馈数据 (feedback/{task_id}.json)

```json
{
  "task_id": "TASK_001",
  "assigned_to_id": "016",
  "assigned_to_name": "李伟员工",
  "chat_history": [
    {
      "timestamp": "2026-03-01 10:00:00",
      "sender": "Agent|用户名",
      "message": "消息内容",
      "message_type": "text|file_upload",
      "file_names": ["file1.pdf", "file2.jpg"]
    }
  ],
  "uploaded_files": [
    {
      "filename": "文件名",
      "file_path": "data/uploads/TASK_001/文件名",
      "upload_time": "2026-03-01 10:30:00",
      "user_id": "016",
      "parse_result": {}
    }
  ],
  "feedback_summary": "反馈总结",
  "summary_timestamp": "2026-03-01 16:00:00",
  "status": "反馈完成",
  "last_updated": "2026-03-01 16:00:00"
}
```

### 3.3 数据访问接口

#### 3.3.1 CSV访问工具

```python
def read_csv_file(filename: str) -> List[Dict]:
    """读取CSV文件"""
    
def write_csv_file(filename: str, data: List[Dict], fieldnames: List[str]) -> bool:
    """写入CSV文件"""
```

#### 3.3.2 JSON访问工具

```python
def read_json_file(filepath: Path) -> Dict:
    """读取JSON文件"""
    
def write_json_file(filepath: Path, data: Dict) -> bool:
    """写入JSON文件"""
```

---

## 四、API设计

### 4.1 API概览

| 分类 | 接口数量 | 说明 |
|------|----------|------|
| 用户接口 | 2 | 用户查询 |
| 任务接口 | 3 | 任务CRUD |
| 风险数据接口 | 2 | 风险数据查询 |
| 反馈接口 | 2 | 反馈数据查询 |
| 聊天接口 | 2 | 消息发送和历史 |
| 文件接口 | 1 | 文件上传 |
| 系统接口 | 1 | 健康检查 |
| **总计** | **13** | |

### 4.2 详细API规范

#### 4.2.1 用户接口

##### GET /api/users
**功能**: 获取所有用户列表

**请求**: 无

**响应**:
```json
[
  {
    "user_id": "001",
    "username": "王经理",
    "role": "业务负责人",
    "department": "风控部",
    "employee_id": "EMP_001"
  }
]
```

---

##### GET /api/users/{user_id}
**功能**: 获取指定用户信息

**请求参数**:
- `user_id` (path): 用户ID

**响应**:
```json
{
  "user_id": "001",
  "username": "王经理",
  "role": "业务负责人",
  "department": "风控部",
  "employee_id": "EMP_001"
}
```

**错误**: 404 - User not found

---

#### 4.2.2 任务接口

##### GET /api/tasks
**功能**: 获取任务列表

**请求参数**:
- `user_id` (query, optional): 用户ID，用于过滤任务

**响应**:
```json
[
  {
    "task_id": "TASK_001",
    "creator_id": "001",
    "creator_name": "王经理",
    "assigned_to_id": "016",
    "assigned_to_name": "李伟员工",
    "status": "反馈完成",
    "created_time": "2026-03-01 10:00",
    "risk_summary": "超时派送风险核查",
    "risk_data_url": "data/risk_data_002.csv"
  }
]
```

---

##### GET /api/tasks/{task_id}
**功能**: 获取指定任务详情

**请求参数**:
- `task_id` (path): 任务ID

**响应**: 同任务列表项

**错误**: 404 - Task not found

---

##### POST /api/tasks
**功能**: 创建新任务

**请求体**:
```json
{
  "creator_id": "001",
  "creator_name": "王经理",
  "assigned_to_id": "016",
  "assigned_to_name": "李伟员工",
  "risk_summary": "超时派送风险核查",
  "risk_data_url": "data/risk_data_002.csv"
}
```

**响应**: 创建的任务信息

---

#### 4.2.3 风险数据接口

##### GET /api/risk-data
**功能**: 获取所有风险数据文件

**响应**:
```json
[
  {
    "filename": "risk_data_001.csv",
    "data": [...],
    "count": 10
  }
]
```

---

##### GET /api/risk-data/{identifier}
**功能**: 获取指定风险数据文件

**请求参数**:
- `identifier` (path): 文件标识（001或risk_data_001.csv）

**响应**:
```json
{
  "filename": "risk_data_001.csv",
  "identifier": "001",
  "data": [...],
  "count": 10
}
```

---

#### 4.2.4 反馈接口

##### GET /api/tasks/{task_id}/creation-history
**功能**: 获取任务创建时的聊天历史

**请求参数**:
- `task_id` (path): 任务ID

**响应**: 聊天历史数组

---

##### GET /api/feedback/{task_id}
**功能**: 获取任务反馈信息

**请求参数**:
- `task_id` (path): 任务ID

**响应**: 反馈数据JSON对象

---

#### 4.2.5 聊天接口

##### POST /api/chat
**功能**: 业务负责人发送消息给ManagerAgent

**请求体**:
```json
{
  "message": "请分析这些风险数据",
  "user_id": "001",
  "username": "王经理"
}
```

**响应**:
```json
{
  "message": "AI回复内容",
  "timestamp": "2026-03-01 10:00:00"
}
```

---

##### GET /api/tasks/{task_id}/chat-history
**功能**: 获取任务聊天历史

**请求参数**:
- `task_id` (path): 任务ID
- `user_id` (query, optional): 用户ID
- `username` (query, optional): 用户名

**响应**: 聊天历史数组

---

##### POST /api/tasks/{task_id}/message
**功能**: 一线人员发送消息给StaffAgent

**请求参数**:
- `task_id` (path): 任务ID

**请求体**:
```json
{
  "message": "核查已完成",
  "user_id": "016",
  "username": "李伟员工"
}
```

**响应**:
```json
{
  "user_message": {...},
  "agent_reply": {...}
}
```

---

#### 4.2.6 文件接口

##### POST /api/tasks/{task_id}/upload-file
**功能**: 上传任务相关文件

**请求参数**:
- `task_id` (path): 任务ID

**请求体** (multipart/form-data):
- `file`: 文件二进制数据
- `user_id`: 用户ID
- `filename`: 文件名

**响应**:
```json
{
  "success": true,
  "message": "文件上传成功",
  "file_path": "data/uploads/TASK_001/文件名"
}
```

---

#### 4.2.7 系统接口

##### GET /api/health
**功能**: 健康检查

**响应**:
```json
{
  "status": "ok",
  "timestamp": "2026-03-01T10:00:00",
  "data_dir": "/path/to/data"
}
```

---

### 4.3 错误码规范

| 错误码 | 说明 | 示例 |
|--------|------|------|
| 400 | 请求参数错误 | {"detail": "未上传文件"} |
| 404 | 资源不存在 | {"detail": "User not found"} |
| 500 | 服务器内部错误 | {"detail": "文件读取失败"} |

---

## 五、前端设计

### 5.1 组件架构

```
App (根组件)
├── LoginPage (登录页面)
│   └── UserSelector (用户选择器)
└── Workspace (工作区)
    ├── AppHeader (顶部导航)
    │   ├── UserInfo (用户信息)
    │   ├── UserSwitch (用户切换)
    │   └── LogoutButton (退出按钮)
    └── MainContent (主内容)
        ├── ManagerWorkspace (业务负责人工作区)
        │   ├── LeftSidebar (左侧栏)
        │   │   ├── RiskDataSection (风险数据区)
        │   │   │   ├── RiskDataTable (数据表格)
        │   │   │   ├── Pagination (分页组件)
        │   │   │   └── ActionButtons (操作按钮)
        │   │   └── TaskListSection (任务列表区)
        │   │       └── TaskCard (任务卡片)
        │   ├── ChatSection (聊天区域)
        │   │   ├── ChatMessages (消息列表)
        │   │   └── ChatInput (输入框)
        │   └── RightSidebar (右侧栏)
        │       └── TaskDetail (任务详情)
        └── StaffWorkspace (一线人员工作区)
            ├── ChatHeader (聊天头部)
            ├── ChatMessages (消息列表)
            └── ChatInput (输入框)
```

### 5.2 状态管理

使用React Hooks进行状态管理：

```javascript
// 用户状态
const [users, setUsers] = useState([])
const [currentUser, setCurrentUser] = useState(null)

// 任务状态
const [tasks, setTasks] = useState([])
const [selectedTask, setSelectedTask] = useState(null)

// 聊天状态
const [chatMessages, setChatMessages] = useState([])
const [inputMessage, setInputMessage] = useState('')

// 风险数据状态
const [allRiskData, setAllRiskData] = useState([])
const [selectedRows, setSelectedRows] = useState([])

// 分页状态
const [currentPage, setCurrentPage] = useState(1)
const [pageSize, setPageSize] = useState(10)

// 加载状态
const [loading, setLoading] = useState({...})
```

### 5.3 样式设计

使用CSS Modules和Flexbox布局：

```css
/* 布局 */
.workspace {
  display: flex;
  height: calc(100vh - 60px);
}

.sidebar {
  width: 35%;
  overflow-y: auto;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 消息样式 */
.message {
  display: flex;
  margin: 10px 0;
}

.message.user {
  justify-content: flex-end;
}

.message.agent {
  justify-content: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 10px 16px;
  border-radius: 8px;
}
```

### 5.4 API客户端

使用原生fetch进行API调用：

```javascript
const API_BASE = 'http://127.0.0.1:5005/api'

// 获取用户列表
const fetchUsers = async () => {
  const response = await fetch(`${API_BASE}/users`)
  return response.json()
}

// 发送消息
const sendMessage = async (message, taskId) => {
  const response = await fetch(`${API_BASE}/tasks/${taskId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      user_id: currentUser.user_id,
      username: currentUser.username
    })
  })
  return response.json()
}
```

---

## 六、Agent设计

### 6.1 Agent架构

```
┌─────────────────────────────────────┐
│         Claude Agent SDK           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         ManagerAgent               │
│  - 分析风险数据                    │
│  - 推荐执行人                      │
│  - 创建任务                        │
└─────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         StaffAgent                 │
│  - 推送任务信息                    │
│  - 指导核查流程                    │
│  - 验证上传文件                    │
│  - 生成反馈总结                    │
└─────────────────────────────────────┘
```

### 6.2 ManagerAgent设计

**System Prompt**:
```
你是一个风险控制专家Agent，负责协助业务负责人完成风险数据的分析、任务分派和反馈管理工作。

你的核心职责：
1. 帮助业务负责人分析上传的风险数据，识别风险特征和关键信息
2. 基于风险数据推荐合适的一线人员进行核查
3. 协助业务负责人完成任务的创建和分派
4. 回答业务负责人关于风险分析方法、任务管理流程的问题
5. 提供风险分析报告和建议
```

**主要方法**:

```python
class ManagerAgent:
    async def __aenter__(self):
        """启动Agent会话"""
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """关闭Agent会话"""
        
    async def chat(self, message: str, context: Optional[Dict] = None) -> str:
        """处理用户消息"""
        
    async def analyze_risk_data(self, file_path: str) -> str:
        """分析风险数据"""
        
    async def recommend_receiver(self, risk_data: str) -> Dict[str, Any]:
        """推荐执行人"""
        
    async def create_task(self, task_info: Dict) -> Dict[str, Any]:
        """创建任务"""
```

### 6.3 StaffAgent设计

**System Prompt**:
```
You are a risk check assistant Agent.

IMPORTANT RULES:
- Reply in Chinese (use Simplified Chinese)
- Be detailed and helpful
- Give specific guidance to users

Your responsibilities:
1. Push task info and risk data to staff
2. Guide staff through verification process
3. Help verify uploaded files
4. Answer questions about tasks
5. Help complete tasks
```

**主要方法**:

```python
class StaffAgent:
    async def __aenter__(self):
        """启动Agent会话"""
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """关闭Agent会话"""
        
    async def init_task(self, task_id: str) -> str:
        """初始化任务，推送任务信息"""
        
    async def chat(self, message: str) -> str:
        """处理一线人员消息"""
        
    async def handle_file_upload(self, file_path: str, file_name: str) -> str:
        """处理文件上传"""
        
    async def complete_task(self) -> Dict[str, Any]:
        """完成任务"""
```

### 6.4 工具函数

**工具列表**:

| 工具名 | 功能 | 输入 | 输出 |
|--------|------|------|------|
| parse_csv | 解析CSV文件 | 文件路径 | 解析结果 |
| parse_excel | 解析Excel文件 | 文件路径, 工作表名 | 解析结果 |
| parse_pdf | 解析PDF文件 | 文件路径, 最大页数 | 文本内容 |
| parse_word | 解析Word文件 | 文件路径 | 文本内容 |
| read_risk_data | 读取风险数据 | 文件名 | 数据内容 |
| list_users | 列出用户 | 角色筛选 | 用户列表 |
| get_task_status | 查询任务状态 | 任务ID | 任务信息 |
| get_task_detail | 获取任务详情 | 任务ID | 任务+反馈 |

---

## 七、会话管理

### 7.1 会话管理器设计

```python
class SessionManager:
    """
    会话管理器 - 管理用户与Agent的会话
    实现用户间隔离、同用户会话复用
    """
    
    # 用户会话缓存
    # key: user_id, value: Agent实例
    _sessions: Dict[str, object] = {}
    
    async def get_or_create_staff_agent(user_id: str, user_name: str) -> StaffAgent:
        """获取或创建StaffAgent"""
        
    async def get_or_create_manager_agent(user_id: str, user_name: str) -> ManagerAgent:
        """获取或创建ManagerAgent"""
        
    async def close_agent(user_id: str):
        """关闭用户会话"""
        
    async def close_all_agents():
        """关闭所有会话"""
```

### 7.2 会话生命周期

```
用户登录 → 检查会话缓存 → 
  ├─ 存在 → 复用会话
  └─ 不存在 → 创建新会话 → 缓存会话

用户操作 → 使用缓存的会话

用户退出/超时 → 关闭会话 → 从缓存移除

服务关闭 → 关闭所有会话
```

---

## 八、安全设计

### 8.1 认证机制

**当前实现**: 基于用户ID的简单认证

```python
def validate_user(user_id: str) -> bool:
    """验证用户ID是否有效"""
    users_file = DATA_DIR / "users.csv"
    # 检查user_id是否存在于users.csv
```

**改进方向**:
- 添加Token认证
- 添加密码验证
- 添加会话过期机制

### 8.2 文件上传安全

**安全措施**:

1. **文件类型限制**
```python
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc'}
```

2. **文件大小限制**
```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```

3. **文件名清理**
```python
import os
filename = os.path.basename(filename)  # 防止路径穿越
```

### 8.3 CORS配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.4 输入验证

**示例**:
```python
if not user_id or not message:
    raise HTTPException(status_code=400, detail="参数不能为空")

if len(message) > 10000:
    raise HTTPException(status_code=400, detail="消息过长")
```

---

## 九、部署方案

### 9.1 开发环境

**后端启动**:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app_fastapi:app --reload --port 5005
```

**前端启动**:
```bash
cd frontend
npm install
npm run dev
```

**访问地址**:
- 前端: http://localhost:5173
- 后端API: http://localhost:5005
- API文档: http://localhost:5005/docs

### 9.2 生产环境（推荐）

#### 方案A: Docker部署

```dockerfile
# Dockerfile (后端)
FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app_fastapi:app", "--host", "0.0.0.0", "--port", "5005"]
```

```dockerfile
# Dockerfile (前端)
FROM node:18-alpine
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build
CMD ["npm", "run", "preview"]
```

```yaml
# docker-compose.yml
version: '3'
services:
  backend:
    build: ./backend
    ports:
      - "5005:5005"
    volumes:
      - ./data:/app/data
  
  frontend:
    build: ./frontend
    ports:
      - "5173:4173"
    depends_on:
      - backend
```

#### 方案B: 云服务部署

- **后端**: Render / Railway / AWS Lambda
- **前端**: Vercel / Netlify / AWS S3
- **数据**: 持久化存储（如AWS EFS）

### 9.3 环境变量

```bash
# .env
ANTHROPIC_BASE_URL=https://api.anthropic.com/v1/messages
ANTHROPIC_AUTH_TOKEN=sk-xxxxxxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
API_TIMEOUT_MS=3000000
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

---

## 十、性能优化

### 10.1 后端优化

| 优化项 | 方案 | 预期效果 |
|--------|------|----------|
| CSV读取 | 使用pandas优化 | 提升50% |
| 文件上传 | 流式上传 | 减少内存占用 |
| 会话管理 | 缓存复用 | 减少初始化时间 |
| 日志记录 | 异步写入 | 减少I/O阻塞 |

### 10.2 前端优化

| 优化项 | 方案 | 预期效果 |
|--------|------|----------|
| 数据加载 | 分页加载 | 减少初始加载时间 |
| 消息列表 | 虚拟滚动 | 支持大量消息 |
| API调用 | 防抖/节流 | 减少请求次数 |
| 组件渲染 | React.memo | 减少重渲染 |

### 10.3 监控指标

```python
# 添加性能监控
import time

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

---

## 十一、测试策略

### 11.1 单元测试

```python
# backend/tests/test_auth.py
def test_validate_user():
    assert validate_user("001") == True
    assert validate_user("999") == False

def test_get_user():
    user = get_user("001")
    assert user["username"] == "王经理"
```

### 11.2 集成测试

```python
# backend/tests/test_api.py
async def test_create_task():
    response = await client.post("/api/tasks", json={...})
    assert response.status_code == 200
```

### 11.3 前端测试

```javascript
// frontend/src/App.test.jsx
test('user can login', async () => {
  render(<App />)
  await waitFor(() => screen.getByText('王经理'))
})
```

---

## 十二、日志与监控

### 12.1 日志配置

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### 12.2 日志级别

| 级别 | 用途 | 示例 |
|------|------|------|
| DEBUG | 调试信息 | 变量值、函数参数 |
| INFO | 一般信息 | API调用、会话创建 |
| WARNING | 警告信息 | SDK降级、文件缺失 |
| ERROR | 错误信息 | API调用失败、文件读取失败 |

---

## 十三、未来扩展

### 13.1 功能扩展

- [ ] WebSocket实时消息推送
- [ ] 任务进度可视化
- [ ] 数据可视化图表
- [ ] 批量任务创建
- [ ] 移动端App
- [ ] 多语言支持

### 13.2 技术扩展

- [ ] 迁移到PostgreSQL数据库
- [ ] 添加Redis缓存
- [ ] 实现消息队列（RabbitMQ/Kafka）
- [ ] 添加OAuth2.0认证
- [ ] 实现微服务架构

### 13.3 AI扩展

- [ ] 支持多模型切换
- [ ] 添加自定义Prompt模板
- [ ] 实现多轮对话记忆
- [ ] 添加知识库检索（RAG）
- [ ] 支持语音交互

---

## 十四、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-03-06 | 初始版本 |

---

**文档状态**: ✅ 已完成  
**维护者**: 开发团队  
**最后审查**: 2026-03-06
