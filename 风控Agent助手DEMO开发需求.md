# 风控Agent助手系统 - DEMO开发需求文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | 风控Agent助手系统 - DEMO开发需求 |
| 版本 | v1.0 |
| 最后更新 | 2026年2月28日 |
| 状态 | 开发中 |

---

## 一、DEMO简化方案概述

### 1.1 核心简化说明

本DEMO是对完整产品需求的精简实现，重点验证以下核心功能：
- ✅ 业务负责人的对话式分析和推送指令下达
- ✅ 一线人员的IM模拟端对话和文件反馈
- ✅ 大模型在数据分析、文件验证、反馈总结中的应用
- ✅ 文件系统的数据持久化

### 1.2 不在本DEMO范围内

- ❌ 用户认证和登录
- ❌ 严格的权限检查（前端过滤，后端基础校验）
- ❌ 复杂的长连接和实时刷新（采用手动刷新）
- ❌ 详细的系统操作日志
- ❌ 性能和并发优化
- ❌ 完整的安全加密

### 1.3 技术架构

```
┌─────────────────────────────────────────┐
│           前端 (React / Vue)             │
│  • 业务负责人工作区 (WEB主智能体)       │
│  • 一线人员工作区 (IM模拟智能体)        │
│  • 用户选择器                           │
└──────────────┬──────────────────────────┘
               │ REST API
┌──────────────▼──────────────────────────┐
│        后端 (Flask / Express)            │
│  • 数据管理和存储                       │
│  • Claude API 集成                      │
│  • 文件上传/下载处理                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│        本地文件系统存储                  │
│  • users.csv (用户信息)                 │
│  • tasks.csv (任务列表)                 │
│  • feedback/*.json (反馈数据)           │
│  • uploads/* (上传的文件)               │
│  • data/* (样例风险数据)                │
└─────────────────────────────────────────┘
```

---

## 二、数据结构和存储方案

### 2.1 用户数据 (users.csv)

**位置**: `/data/users.csv`

**字段定义**:
```csv
user_id,username,role,department,employee_id
001,李经理,业务负责人,风控部,
002,张分析,普通分析人员,风控部,
003,快递小哥,一线操作人员,快递部,EMP_001
004,销售A,一线操作人员,销售部,EMP_002
005,销售B,一线操作人员,销售部,EMP_003
```

**字段说明**:
- `user_id`: 用户唯一标识
- `username`: 用户显示名称
- `role`: 用户角色 (业务负责人 / 普通分析人员 / 一线操作人员)
- `department`: 部门名称
- `employee_id`: 员工ID (仅一线人员有此ID)

---

### 2.2 任务列表 (tasks.csv)

**位置**: `/data/tasks.csv`

**字段定义**:
```csv
task_id,creator_id,creator_name,assigned_to_id,assigned_to_name,status,created_time,risk_summary,risk_data_url,suggested_receiver_id,confirmed_receiver_id,completed_time
TASK_001,001,李经理,003,快递小哥,已完成,2025-02-28 10:00,快递员工异常交易识别,data/risk_data_001.csv,003,003,2025-02-28 15:30
TASK_002,001,李经理,004,销售A,进行中,2025-02-28 11:00,销售部员工风险核查,data/risk_data_002.csv,004,004,
```

**字段说明**:
- `task_id`: 任务唯一标识 (格式: TASK_XXXX)
- `creator_id`: 创建任务的业务负责人ID
- `creator_name`: 创建任务的业务负责人名称
- `assigned_to_id`: 分配给的一线人员ID (DEMO阶段仅一个人)
- `assigned_to_name`: 分配给的一线人员名称
- `status`: 任务状态 (待处理 / 进行中 / 已完成 / 已超期)
- `created_time`: 任务创建时间 (格式: YYYY-MM-DD HH:MM)
- `risk_summary`: 风险简述
- `risk_data_url`: 风险明细数据文件的URL (相对路径，如 data/risk_data_001.csv)
- `suggested_receiver_id`: AI推荐的接收人ID (用于记录推荐逻辑)
- `confirmed_receiver_id`: 业务负责人确认的接收人ID (可能与AI推荐不同)
- `completed_time`: 任务完成时间 (格式: YYYY-MM-DD HH:MM)

---

### 2.3 反馈数据 (feedback/{task_id}.json)

**位置**: `/data/feedback/TASK_001.json`

**结构定义**:
```json
{
  "task_id": "TASK_001",
  "assigned_to_id": "003",
  "assigned_to_name": "快递小哥",
  "chat_history": [
    {
      "timestamp": "2025-02-28 10:05:00",
      "sender": "Agent",
      "message": "您好，请核查以下员工信息。风险类型：交易异常。详见风险数据文件。请在24小时内提交核查结果。",
      "message_type": "text"
    },
    {
      "timestamp": "2025-02-28 10:10:00",
      "sender": "快递小哥",
      "message": "收到，我已查看风险数据。会尽快完成核查。",
      "message_type": "text"
    },
    {
      "timestamp": "2025-02-28 10:15:00",
      "sender": "Agent",
      "message": "感谢反馈。请上传核查结果文件。要求：1) 核查单需包含员工确认信息 2) 如有证明文件，请上传清晰的照片。",
      "message_type": "text"
    },
    {
      "timestamp": "2025-02-28 10:30:00",
      "sender": "快递小哥",
      "message": "已上传核查单和证明照片",
      "message_type": "file_upload",
      "file_names": ["核查单.pdf", "证明照片.jpg"]
    }
  ],
  "uploaded_files": [
    {
      "filename": "核查单.pdf",
      "upload_time": "2025-02-28 10:30:00",
      "file_path": "uploads/TASK_001/003/核查单.pdf",
      "file_size": 245000,
      "verification_status": "合格",
      "verification_details": "文件内容完整，包含核查人员确认信息"
    },
    {
      "filename": "证明照片.jpg",
      "upload_time": "2025-02-28 10:30:00",
      "file_path": "uploads/TASK_001/003/证明照片.jpg",
      "file_size": 1204000,
      "verification_status": "合格",
      "verification_details": "图片清晰，可以清楚识别证件信息"
    }
  ],
  "feedback_summary": "快递小哥已确认所属部门员工在2025-02-25 14:30进行了异常交易（金额5000元）。已收集该员工的身份证复印件和交易记录截图。该员工已承认交易行为，声称系误操作。建议：1) 与员工再次沟通确认 2) 监控后续交易行为 3) 考虑加强员工的交易规范培训。风险等级评估：中等风险，已初步得到解释，需继续跟踪。",
  "summary_timestamp": "2025-02-28 10:35:00",
  "verification_timestamp": "2025-02-28 10:35:00",
  "status": "completed"
}
```

**数据说明**:
- `chat_history`: 完整的对话记录，包含时间戳、发送者、消息内容和消息类型
- `message_type`: 消息类型 (text / file_upload)
- `file_names`: 当消息类型为file_upload时，包含上传的文件列表
- `uploaded_files`: 所有上传文件的详细信息，包括验证状态和验证详情
- `verification_status`: 文件验证状态 (合格 / 不合格 / 待验证)
- `verification_details`: AI验证的具体反馈内容
- `feedback_summary`: AI生成的反馈分析总结 (在任务完成时生成)
- `status`: 反馈状态 (进行中 / 已提交 / 已验证 / completed)

---

### 2.4 样例风险数据 (data/risk_data_XXX.csv)

**位置**: `/data/risk_data_001.csv` (业务负责人上传或选择的风险明细)

**示例内容**:
```csv
员工姓名,岗位,部门,员工ID,交易金额,交易时间,异常类型,风险等级
张三,快递员,快递部,EMP_001,5000,2025-02-25 14:30,交易异常,高
李四,销售经理,销售部,EMP_002,12000,2025-02-26 09:15,超额消费,中
王五,快递员,快递部,EMP_001,3000,2025-02-27 16:45,频繁交易,低
```

**字段说明**:
- 风险数据包含员工的姓名和岗位等关键信息
- AI会基于这些信息识别推荐的接收人（通过员工名字和部门匹配）

---

### 2.5 本地数据文件结构

```
项目根目录/
├── data/
│   ├── users.csv (用户信息)
│   ├── tasks.csv (任务列表)
│   ├── risk_data_001.csv (示例风险数据)
│   ├── risk_data_002.csv (示例风险数据)
│   ├── risk_data_003.csv (示例风险数据)
│   └── feedback/
│       ├── TASK_001.json
│       ├── TASK_002.json
│       └── ...
├── uploads/
│   ├── TASK_001/
│   │   └── 003/
│   │       ├── 核查单.pdf
│   │       └── 证明照片.jpg
│   ├── TASK_002/
│   │   └── 004/
│   │       └── ...
│   └── ...
├── backend/
│   ├── app.py (或 app.js)
│   ├── routes.py (或 routes.js)
│   ├── utils.py (或 utils.js)
│   └── requirements.txt (或 package.json)
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
└── README.md
```

---

## 三、核心功能模块

### 3.1 业务负责人工作区 (WEB主智能体)

#### 功能1：上传或选择风险数据

**业务流程**:
1. 业务负责人在WEB界面上传CSV文件，或选择本地预置的风险数据
2. 后端读取CSV文件内容
3. 解析数据并呈现给前端（如数据预览）

**关键API**:
- `POST /api/upload-risk-data` - 上传风险数据文件
- `GET /api/sample-data` - 获取预置的风险数据列表

**前端交互**:
- 文件上传组件或下拉选择框
- 数据预览表格

---

#### 功能2：对话式分析

**业务流程**:
1. 业务负责人与AI Agent进行对话，要求AI分析风险数据
2. AI返回分析结果（如风险汇总、涉及的员工等）
3. 业务负责人可进行多轮对话，迭代优化分析结果

**关键API**:
- `POST /api/analyze` - 调用Claude API分析风险数据
  - 输入: 风险数据内容、用户当前的对话消息
  - 输出: AI的分析结果

**Claude Prompt设计**:
```
你是一个风险控制分析师。用户上传了一份风险数据，包含以下字段：
[列出CSV中的字段]

当前数据内容：
[CSV内容]

请分析这份数据，并回答用户的问题。
如果数据包含多个员工信息，请逐个列出。
```

**前端交互**:
- 对话框：用户输入分析需求
- 消息历史展示
- Agent的分析结果展示

---

#### 功能3：推荐接收人并确认下达

**业务流程**:
1. 业务负责人确认推送内容后，点击"下达推送指令"
2. 后端调用Claude API，基于风险数据中的员工信息推荐接收人
3. 前端显示AI推荐的接收人
4. 业务负责人可确认或修改推荐的接收人（DEMO阶段仅一个人）
5. 确认后，创建任务并存储到tasks.csv和feedback JSON文件

**关键API**:
- `POST /api/recommend-receiver` - 调用Claude API推荐接收人
  - 输入: 风险数据内容、所有一线人员列表
  - 输出: 推荐的接收人ID和推荐理由

**Claude Prompt设计**:
```
你是一个任务分配助手。现有以下风险数据和一线人员信息：

风险数据：
[员工姓名、部门等信息]

可用的一线人员：
- 快递小哥 (快递部)
- 销售A (销售部)
- 销售B (销售部)

请根据风险数据中的员工信息，推荐最适合的一线人员来核查。
返回推荐的人员名字和推荐理由。
```

**关键逻辑**:
- 假设风险数据中的员工姓名唯一不重复
- AI基于员工的部门或其他特征识别推荐的接收人
- 如果无法匹配，系统提示"无合适接收人"

**前端交互**:
- 推荐结果展示（推荐人 + 推荐理由）
- "确认"按钮
- 修改接收人的下拉选择框（可选）

---

### 3.2 一线人员工作区 (IM模拟智能体)

#### 功能1：查看待处理任务

**业务流程**:
1. 一线人员进入工作区，查看分配给自己的所有任务
2. 任务以列表形式展示，包括：任务ID、风险简述、创建时间、状态

**关键API**:
- `GET /api/tasks?user_id=xxx&role=一线操作人员` - 获取当前用户的任务列表

**前端交互**:
- 任务列表（卡片式或表格式）
- 任务状态徽章（待处理、进行中、已完成）
- 点击任务卡片进入对话页面

---

#### 功能2：IM风格对话和文件上传

**业务流程**:
1. 一线人员点击任务进入对话页面
2. 页面顶部显示风险数据文件链接（可下载查看）
3. 中间为对话区域，展示Agent的初始消息和历史对话
4. 对话区域支持：文本消息输入、文件上传
5. 下方为文件上传区域，显示已上传文件列表

**关键API**:
- `GET /api/tasks/{task_id}` - 获取任务详情（包括风险数据URL）
- `GET /api/tasks/{task_id}/chat-history` - 获取对话历史
- `POST /api/tasks/{task_id}/message` - 发送文本消息
  - 输入: 消息内容
  - 输出: AI的回复（调用Claude API）
- `POST /api/tasks/{task_id}/upload-file` - 上传文件
  - 输入: 文件内容
  - 输出: 文件保存路径、验证结果

**Claude Prompt设计（对话回复）**:
```
你是一个风险核查助手。你正在协助一线人员核查以下风险任务：

任务ID: {task_id}
风险简述: {risk_summary}
风险数据: [CSV数据内容]

一线人员的消息: {user_message}

请基于风险数据和用户的消息，给出专业的回复。
如果用户询问如何核查，请给出具体的步骤。
如果用户已上传文件，请提醒还需要上传哪些文件。
```

**IM风格UI要求**:
- 消息气泡（Agent左对齐，一线人员右对齐）
- 时间戳（精确到分钟）
- 发送者信息（Agent / 用户名）
- 文件消息显示文件名和上传时间

**前端交互**:
- 文本输入框 + 发送按钮
- 文件上传按钮
- 对话历史自动滚动到最新消息
- 已上传文件列表（包括验证状态）

---

#### 功能3：文件验证和反馈

**业务流程**:
1. 一线人员上传文件后，后端立即调用Claude API验证文件内容
2. 验证包括：文件是否为空、图片是否清晰、内容是否合规等
3. 验证结果立即返回给前端
4. 如果验证不合格，显示具体的改进建议
5. 一线人员可重新上传文件或继续对话

**关键API**:
- `POST /api/tasks/{task_id}/verify-files` - 调用Claude API验证上传的文件
  - 输入: 文件路径、文件名、文件类型
  - 输出: 验证状态 (合格 / 不合格)、验证详情（改进建议）

**文件验证的Claude Prompt**:
```
你是一个文件质量检查助手。需要检查以下上传的文件：

文件名: {filename}
文件类型: {file_type}
风险任务: {risk_summary}

请检查：
1. 文件是否为空（如果是PDF，是否有文本内容）
2. 图片是否清晰（如果是图片，是否可以清楚识别内容）
3. 文件内容是否与风险核查相关

返回检查结果：
- 状态：合格 / 不合格
- 如果不合格，请给出具体的改进建议
```

**文件验证逻辑**:
- 逐个文件验证
- 验证结果实时展示
- 不合格文件显示具体原因和改进建议

**前端交互**:
- 已上传文件列表，每个文件显示：
  - 文件名
  - 上传时间
  - 验证状态（待验证 / 合格 / 不合格）
  - 验证详情（如验证不合格，显示建议）
- 重新上传按钮（如验证不合格）

---

#### 功能4：确认完成和生成总结

**业务流程**:
1. 所有必需文件验证合格后，一线人员点击"确认完成"
2. 后端调用Claude API，基于对话历史和上传的文件内容生成反馈总结
3. 反馈总结、对话历史和文件列表一起保存到feedback JSON文件
4. 任务状态更新为"已完成"
5. 一线人员页面显示"任务已完成"提示

**关键API**:
- `POST /api/tasks/{task_id}/complete` - 完成任务并生成总结
  - 输入: task_id、chat_history、uploaded_files列表
  - 输出: feedback_summary、completion status

**生成总结的Claude Prompt**:
```
你是一个风险核查总结专家。请基于以下信息生成本次核查的总结：

风险任务信息:
- 风险简述: {risk_summary}
- 原始数据: [CSV数据]

对话历史:
[完整的对话记录]

上传的文件:
[文件名列表及验证结果]

请生成一份专业的核查总结，包括：
1. 本次核查的关键发现
2. 一线人员提交的证明材料说明
3. 风险等级评估
4. 建议的后续处理措施
5. 核查的完整性评价

总结应该简洁清晰，1000字以内。
```

**前端交互**:
- "确认完成"按钮
- 完成后显示提示："任务已完成，反馈总结已生成"
- 可选：显示生成的反馈总结预览

---

### 3.3 用户选择和页面导航

**业务流程**:
1. 首次进入系统，显示用户选择界面
2. 用户选择自己的身份后，进入对应的工作区
3. 工作区顶部显示当前用户信息和"切换用户"按钮

**关键API**:
- `GET /api/users` - 获取所有用户信息

**前端交互**:
- 用户选择下拉框或卡片列表
- 按角色分组显示（业务负责人 / 普通分析人员 / 一线操作人员）
- 选择后进入对应工作区

---

## 四、后端API详细规范

### 4.1 用户相关API

#### GET /api/users
获取所有用户信息

**请求**:
```
GET /api/users
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "成功",
  "data": [
    {
      "user_id": "001",
      "username": "李经理",
      "role": "业务负责人",
      "department": "风控部",
      "employee_id": null
    },
    ...
  ]
}
```

---

#### GET /api/users/{user_id}
获取单个用户信息

**请求**:
```
GET /api/users/001
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "user_id": "001",
    "username": "李经理",
    "role": "业务负责人",
    "department": "风控部",
    "employee_id": null
  }
}
```

---

### 4.2 任务相关API

#### GET /api/tasks
获取任务列表（支持过滤）

**请求**:
```
GET /api/tasks?user_id=001&role=业务负责人
```

**查询参数**:
- `user_id`: 用户ID（必填）
- `role`: 用户角色（可选，用于权限过滤）

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "成功",
  "data": [
    {
      "task_id": "TASK_001",
      "creator_id": "001",
      "creator_name": "李经理",
      "assigned_to_id": "003",
      "assigned_to_name": "快递小哥",
      "status": "已完成",
      "created_time": "2025-02-28 10:00",
      "risk_summary": "快递员工异常交易识别",
      "risk_data_url": "data/risk_data_001.csv",
      "completed_time": "2025-02-28 15:30"
    },
    ...
  ]
}
```

---

#### GET /api/tasks/{task_id}
获取任务详情

**请求**:
```
GET /api/tasks/TASK_001
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "task_id": "TASK_001",
    "creator_id": "001",
    "creator_name": "李经理",
    "assigned_to_id": "003",
    "assigned_to_name": "快递小哥",
    "status": "已完成",
    "created_time": "2025-02-28 10:00",
    "risk_summary": "快递员工异常交易识别",
    "risk_data_url": "data/risk_data_001.csv",
    "suggested_receiver_id": "003",
    "confirmed_receiver_id": "003",
    "completed_time": "2025-02-28 15:30"
  }
}
```

---

#### POST /api/tasks
创建新任务

**请求**:
```json
{
  "creator_id": "001",
  "creator_name": "李经理",
  "assigned_to_id": "003",
  "assigned_to_name": "快递小哥",
  "risk_summary": "快递员工异常交易识别",
  "risk_data_url": "data/risk_data_001.csv",
  "suggested_receiver_id": "003",
  "confirmed_receiver_id": "003"
}
```

**响应** (201 Created):
```json
{
  "code": 0,
  "message": "任务创建成功",
  "data": {
    "task_id": "TASK_001",
    "created_time": "2025-02-28 10:00"
  }
}
```

**后端逻辑**:
1. 生成新的task_id
2. 将任务信息追加到tasks.csv
3. 创建对应的feedback JSON文件（初始状态为空对话历史）
4. 创建上传文件的目录：`/uploads/{task_id}/{assigned_to_id}/`

---

### 4.3 数据分析相关API

#### POST /api/upload-risk-data
上传风险数据文件

**请求** (multipart/form-data):
```
POST /api/upload-risk-data
Content-Type: multipart/form-data

file: [CSV文件内容]
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "文件上传成功",
  "data": {
    "file_path": "data/risk_data_uploaded_20250228_100000.csv",
    "file_name": "risk_data.csv",
    "rows": 5,
    "columns": ["员工姓名", "岗位", "部门", "员工ID", "交易金额", "交易时间", "异常类型", "风险等级"]
  }
}
```

---

#### GET /api/sample-data
获取预置的样例风险数据列表

**请求**:
```
GET /api/sample-data
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "成功",
  "data": [
    {
      "file_name": "快递部风险数据",
      "file_path": "data/risk_data_001.csv",
      "rows": 3,
      "description": "包含快递部员工的异常交易数据"
    },
    {
      "file_name": "销售部风险数据",
      "file_path": "data/risk_data_002.csv",
      "rows": 4,
      "description": "包含销售部员工的风险核查数据"
    }
  ]
}
```

---

#### POST /api/analyze
调用Claude API分析风险数据

**请求**:
```json
{
  "risk_data_path": "data/risk_data_001.csv",
  "user_message": "请分析这份数据中有哪些风险员工？"
}
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "分析成功",
  "data": {
    "analysis": "根据风险数据分析，涉及以下风险员工：\n1. 张三 (快递部) - 交易异常，金额5000元，风险等级高\n2. 李四 (销售部) - 超额消费...",
    "tokens_used": 1234
  }
}
```

**后端逻辑**:
1. 读取CSV文件内容
2. 调用Claude API，使用Prompt进行分析
3. 返回分析结果

---

#### POST /api/recommend-receiver
推荐接收人

**请求**:
```json
{
  "risk_data_path": "data/risk_data_001.csv",
  "available_users": [
    {
      "user_id": "003",
      "username": "快递小哥",
      "department": "快递部"
    },
    {
      "user_id": "004",
      "username": "销售A",
      "department": "销售部"
    }
  ]
}
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "推荐成功",
  "data": {
    "recommended_user_id": "003",
    "recommended_user_name": "快递小哥",
    "reason": "风险数据中涉及快递部员工张三，建议由快递小哥进行核查"
  }
}
```

**后端逻辑**:
1. 读取CSV文件内容
2. 调用Claude API，使用Prompt推荐接收人
3. 解析Claude返回的结果，提取推荐人ID

---

### 4.4 对话和反馈相关API

#### GET /api/tasks/{task_id}/chat-history
获取任务的对话历史

**请求**:
```
GET /api/tasks/TASK_001/chat-history
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "task_id": "TASK_001",
    "chat_history": [
      {
        "timestamp": "2025-02-28 10:05:00",
        "sender": "Agent",
        "message": "您好，请核查以下员工信息...",
        "message_type": "text"
      },
      {
        "timestamp": "2025-02-28 10:10:00",
        "sender": "快递小哥",
        "message": "收到，我已查看风险数据...",
        "message_type": "text"
      }
    ]
  }
}
```

---

#### POST /api/tasks/{task_id}/message
发送消息（一线人员发送文本消息，系统调用Claude API回复）

**请求**:
```json
{
  "user_id": "003",
  "username": "快递小哥",
  "message": "我已经查看了风险数据，正在核查员工情况"
}
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "消息已发送并获得回复",
  "data": {
    "user_message": {
      "timestamp": "2025-02-28 10:10:00",
      "sender": "快递小哥",
      "message": "我已经查看了风险数据，正在核查员工情况",
      "message_type": "text"
    },
    "agent_reply": {
      "timestamp": "2025-02-28 10:10:05",
      "sender": "Agent",
      "message": "感谢反馈。请继续核查，并在完成后上传相关证明文件。...",
      "message_type": "text"
    }
  }
}
```

**后端逻辑**:
1. 保存一线人员的消息到内存/临时存储
2. 调用Claude API生成Agent回复
3. 返回两条消息（用户 + Agent）
4. 仅在任务完成时，将所有消息持久化到feedback JSON

---

#### POST /api/tasks/{task_id}/upload-file
上传文件

**请求** (multipart/form-data):
```
POST /api/tasks/TASK_001/upload-file
Content-Type: multipart/form-data

user_id: 003
file: [文件内容]
filename: 核查单.pdf
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "文件上传成功",
  "data": {
    "filename": "核查单.pdf",
    "file_path": "uploads/TASK_001/003/核查单.pdf",
    "upload_time": "2025-02-28 10:30:00",
    "file_size": 245000,
    "verification_status": "验证中...",
    "next_step": "请等待验证结果"
  }
}
```

**后端逻辑**:
1. 将文件保存到 `/uploads/{task_id}/{user_id}/`
2. 立即调用 `/api/tasks/{task_id}/verify-files` 进行验证
3. 返回文件保存结果（验证异步进行）

---

#### POST /api/tasks/{task_id}/verify-files
验证上传的文件内容

**请求**:
```json
{
  "file_path": "uploads/TASK_001/003/核查单.pdf",
  "filename": "核查单.pdf",
  "file_type": "pdf",
  "risk_summary": "快递员工异常交易识别"
}
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "文件验证完成",
  "data": {
    "filename": "核查单.pdf",
    "verification_status": "合格",
    "verification_details": "文件内容完整，包含核查人员确认信息",
    "verified_time": "2025-02-28 10:30:30"
  }
}
```

**验证失败的响应示例** (200 OK):
```json
{
  "code": 0,
  "message": "文件验证完成",
  "data": {
    "filename": "证明照片.jpg",
    "verification_status": "不合格",
    "verification_details": "图片清晰度不足，无法识别证件信息。建议：请重新拍照，确保光线充足，证件信息清晰可见",
    "verified_time": "2025-02-28 10:35:00"
  }
}
```

**后端逻辑**:
1. 读取文件内容（或文件路径）
2. 调用Claude API的vision能力（如果是图片）或文本分析
3. 返回验证结果
4. 更新feedback JSON中的文件验证状态

---

#### POST /api/tasks/{task_id}/complete
完成任务并生成总结

**请求**:
```json
{
  "user_id": "003",
  "task_id": "TASK_001"
}
```

**响应** (200 OK):
```json
{
  "code": 0,
  "message": "任务已完成，反馈总结已生成",
  "data": {
    "task_id": "TASK_001",
    "status": "已完成",
    "feedback_summary": "快递小哥已确认所属部门员工在2025-02-25 14:30进行了异常交易...",
    "summary_timestamp": "2025-02-28 10:35:00"
  }
}
```

**后端逻辑**:
1. 获取完整的对话历史（从内存/临时存储中）
2. 获取所有上传的文件列表和验证结果
3. 调用Claude API生成反馈总结
4. 将对话历史、文件列表、反馈总结保存到feedback JSON文件
5. 更新tasks.csv中的任务状态为"已完成"和完成时间
6. 清除临时的对话存储

---

## 五、前端页面布局（待补充）

用户将在后续提供详细的页面布局设计图片，前端需要根据以下功能区域进行开发：

### 5.1 业务负责人工作区

- [ ] 用户信息和切换用户区域
- [ ] 数据上传/选择区域
- [ ] 对话式分析区域
- [ ] 任务推荐和确认区域
- [ ] 任务列表和进度查看区域

### 5.2 一线人员工作区

- [ ] 用户信息和切换用户区域
- [ ] 待处理任务列表
- [ ] 对话页面：
  - [ ] 风险信息展示和文件下载
  - [ ] IM风格对话区域（消息气泡、时间戳）
  - [ ] 文件上传区域
  - [ ] 已上传文件列表（验证状态）
  - [ ] "确认完成"按钮

### 5.3 用户选择界面

- [ ] 用户列表（按角色分组）
- [ ] 选择后进入对应工作区

---

## 六、技术栈选型（待确认）

### 后端候选方案
- **Python + Flask** (推荐，集成Claude SDK方便)
- **Node.js + Express**

### 前端候选方案
- **React** (推荐)
- **Vue.js**

---

## 七、开发时间线和里程碑

### Phase 1: 基础框架和数据结构（1-2天）
- [ ] 后端框架搭建
- [ ] 数据文件结构定义
- [ ] 样例数据准备

### Phase 2: 业务负责人工作区（2-3天）
- [ ] 数据上传/选择功能
- [ ] 对话式分析（集成Claude API）
- [ ] 推荐接收人（集成Claude API）
- [ ] 任务创建和下达

### Phase 3: 一线人员工作区（2-3天）
- [ ] 任务列表展示
- [ ] IM风格对话功能
- [ ] 文件上传和验证（集成Claude API）
- [ ] 任务完成和反馈总结（集成Claude API）

### Phase 4: 集成和测试（1-2天）
- [ ] 前后端联调
- [ ] 完整流程测试
- [ ] Bug修复和优化

**总计预期：6-10天**

---

## 八、关键技术细节

### 8.1 Claude API集成

**需要集成的4个场景**:
1. **风险数据分析** (POST /api/analyze)
2. **推荐接收人** (POST /api/recommend-receiver)
3. **文件内容验证** (POST /api/tasks/{task_id}/verify-files)
4. **反馈总结生成** (POST /api/tasks/{task_id}/complete)

**API调用方式** (以Python Flask为例):
```python
from anthropic import Anthropic

client = Anthropic()

def analyze_risk_data(risk_data_content, user_message):
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""你是一个风险控制分析师...

风险数据：
{risk_data_content}

用户问题：{user_message}
"""
            }
        ]
    )
    return response.content[0].text
```

---

### 8.2 文件处理

**文件上传处理**:
```python
# 后端接收文件
UPLOAD_DIR = "uploads"

@app.route('/api/tasks/<task_id>/upload-file', methods=['POST'])
def upload_file(task_id):
    file = request.files['file']
    user_id = request.form['user_id']

    # 创建目录
    upload_path = f"{UPLOAD_DIR}/{task_id}/{user_id}"
    os.makedirs(upload_path, exist_ok=True)

    # 保存文件
    file_path = f"{upload_path}/{file.filename}"
    file.save(file_path)

    # 验证文件
    verify_result = verify_file(file_path, file.filename)

    return {
        "file_path": file_path,
        "verification_status": verify_result["status"],
        ...
    }
```

---

### 8.3 数据持久化

**CSV操作** (使用pandas):
```python
import pandas as pd

# 读取tasks.csv
tasks_df = pd.read_csv('data/tasks.csv')

# 追加新任务
new_task = {
    'task_id': 'TASK_001',
    'creator_id': '001',
    ...
}
tasks_df = pd.concat([tasks_df, pd.DataFrame([new_task])], ignore_index=True)

# 保存
tasks_df.to_csv('data/tasks.csv', index=False)
```

**JSON操作** (反馈数据):
```python
import json

# 读取反馈
with open(f'data/feedback/{task_id}.json', 'r') as f:
    feedback = json.load(f)

# 更新对话历史
feedback['chat_history'].append({
    'timestamp': datetime.now().isoformat(),
    'sender': 'Agent',
    'message': '...',
    'message_type': 'text'
})

# 保存
with open(f'data/feedback/{task_id}.json', 'w') as f:
    json.dump(feedback, f, ensure_ascii=False, indent=2)
```

---

## 九、测试和验证清单

### 业务负责人工作区
- [ ] 上传CSV文件并正确解析
- [ ] 选择样例风险数据
- [ ] 与AI进行多轮对话分析
- [ ] AI推荐接收人逻辑正确
- [ ] 修改推荐的接收人
- [ ] 创建任务并生成task_id
- [ ] tasks.csv和feedback JSON正确生成
- [ ] 查看任务列表和进度

### 一线人员工作区
- [ ] 看到分配给自己的任务
- [ ] 打开任务后看到风险数据文件链接
- [ ] 查看对话历史（首次为空或包含初始消息）
- [ ] 发送文本消息，AI正确回复
- [ ] 上传单个或多个文件
- [ ] 文件验证正确（合格/不合格）
- [ ] 验证失败时显示改进建议
- [ ] 点击"确认完成"生成反馈总结
- [ ] 任务状态更新为"已完成"
- [ ] feedback JSON正确保存（包含chat_history和feedback_summary）

### 数据持久化
- [ ] users.csv正确加载和显示
- [ ] tasks.csv正确更新和查询
- [ ] feedback JSON正确生成和读取
- [ ] 文件上传到正确的目录
- [ ] 数据一致性检查

---

## 十、其他说明

### 10.1 约定俗成

- 所有时间格式采用：`YYYY-MM-DD HH:MM` 或 `YYYY-MM-DD HH:MM:SS`
- 所有文件路径采用相对路径（相对于项目根目录）
- CSV编码采用UTF-8
- JSON编码采用UTF-8

### 10.2 错误处理

后端API需要统一的错误响应格式：

**错误响应示例** (400 Bad Request):
```json
{
  "code": -1,
  "message": "错误描述信息",
  "data": null
}
```

---

**文档完成**
