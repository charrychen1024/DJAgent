# 风控Agent助手系统 - DEMO开发需求文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | 风控Agent助手系统 - DEMO开发需求 |
| 版本 | v1.2 |
| 最后更新 | 2026年3月3日 |
| 状态 | 开发中（待接入Claude Agent SDK） |

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
│           前端 (React 18 + Vite)        │
│  • 业务负责人工作区 (WEB主智能体)       │
│  • 一线人员工作区 (IM模拟智能体)        │
│  • 用户选择器                           │
└──────────────┬──────────────────────────┘
               │ REST API / WebSocket
┌──────────────▼──────────────────────────┐
│        后端 (FastAPI)                  │
│  • 异步数据管理和存储                   │
│  • 智能体服务集成 (Manager/Staff)       │
│  • 文件上传/下载处理                    │
│  • CORS跨域支持                         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    智能体服务层 (agents/)                │
│  • ManagerAgent - 业务负责人智能体      │
│  • StaffAgent - 一线人员智能体          │
│  • SessionManager - 会话管理            │
│  • Tools - 工具函数 (查询、创建任务等)    │
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
TASK_001,001,李经理,003,快递小哥,反馈完成,2025-02-28 10:00,运单WLYD001重量异常核查,data/risk_data_001.csv,003,003,2025-02-28 15:30
TASK_002,001,李经理,004,销售A,已下发,2025-02-28 11:00,运单WLYD002超时派送核查,data/risk_data_002.csv,004,004,
```

**字段说明**:
- `task_id`: 任务唯一标识 (格式: TASK_XXXX)
- `creator_id`: 创建任务的业务负责人ID
- `creator_name`: 创建任务的业务负责人名称
- `assigned_to_id`: 分配给的一线人员ID (DEMO阶段仅一个人)
- `assigned_to_name`: 分配给的一线人员名称
- `status`: 任务状态 (已创建 / 已下发 / 反馈完成 / 已超期)
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
      "filename": "运单核查单.pdf",
      "upload_time": "2025-02-28 10:30:00",
      "file_path": "uploads/TASK_001/003/运单核查单.pdf",
      "file_size": 245000
    },
    {
      "filename": "货物重量证明.jpg",
      "upload_time": "2025-02-28 10:30:00",
      "file_path": "uploads/TASK_001/003/货物重量证明.jpg",
      "file_size": 1204000
    }
  ],
  "feedback_summary": "快递小哥已核查运单WLYD001的重量异常问题。确认实际货物重量为14.8kg，与运单填写的15kg相符，属于测量误差。已上传货物称重照片和运单核查单。建议：1) 对运单填写规范进行培训 2) 对货物称重设备进行校准 3) 监控后续同类运单的称重准确性。风险等级评估：中等风险，属于操作误差，已得到合理解释。",
  "summary_timestamp": "2025-02-28 10:35:00",
  "verification_timestamp": "2025-02-28 10:35:00",
  "status": "completed"
}
```

**数据说明**:
- `chat_history`: 完整的对话记录，包含时间戳、发送者、消息内容和消息类型
- `message_type`: 消息类型 (text / file_upload)
- `file_names`: 当消息类型为file_upload时，包含上传的文件列表
- `uploaded_files`: 所有上传文件的详细信息
- 所有文件验证都是通过IM对话方式完成的，AI大模型会自动校验文件内容，并将校验结果通过对话发给一线人员
- `feedback_summary`: AI生成的反馈分析总结 (在任务完成时生成)
- `status`: 反馈状态 (已创建 / 已下发 / 反馈完成 / 已超期)

---

### 2.4 样例风险数据 (data/risk_data_XXX.csv)

**位置**: `/data/risk_data_001.csv` (业务负责人上传或选择的风险明细)

**示例内容**:
```csv
运单号,发货地,收货地,揽收人,揽收人ID,客户名称,供应商名称,货物类型,产品类型,重量,体积,运费金额,结算金额,发货时间,揽收时间,派件时间,签收时间,运单状态,对账人,公里数,发货网点,收货网点,异常类型,风险等级
WLYD001,上海浦东新区,北京朝阳区,张三,EMP_001,ABC贸易公司,顺丰物流,电子产品,零担,15kg,0.12m³,280元,260元,2025-02-25 09:00,2025-02-25 10:30,2025-02-26 14:00,2025-02-26 15:30,已签收,李四,1200km,上海浦东网点,北京朝阳网点,重量异常,高
WLYD002,广州天河区,深圳南山区,李四,EMP_002,XYZ科技公司,圆通速递,服装,整车,2.5吨,3.2m³,1200元,1150元,2025-02-26 08:30,2025-02-26 09:45,2025-02-26 13:30,2025-02-26 14:15,已签收,王五,150km,广州天河网点,深圳南山网点,超时派送,中
WLYD003,杭州余杭区,南京鼓楼区,王五,EMP_003,DEF制造公司,韵达快运,食品,零担,8kg,0.08m³,150元,140元,2025-02-27 10:00,2025-02-27 11:20,2025-02-28 09:30,,派送中,赵六,280km,杭州余杭网点,南京鼓楼网点,未及时签收,低
```

**字段说明**:
- 风险数据包含完整的物流运单信息，贴近实际业务场景
- 揽收人ID字段便于与用户数据匹配
- 产品类型区分整车/零担/合同物流
- 运单状态和异常类型字段便于智能体识别风险
- 风险等级分为低、中、高三类

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

## 三、前端页面布局设计

### 3.1 Web智能体前端页面布局 (业务负责人/普通分析人员)

**布局结构**: 左中右三栏式布局，所有栏均可自由调节大小

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 风险Agent助手系统 - 业务负责人工作区                                      │
├─────────────┬──────────────────────┬─────────────────────────────────────┤
│   左侧栏    │   中间栏              │   右侧栏                            │
│  (可调节)  │  (可调节，主要区域)    │  (可调节，辅助展示区)                │
├─────────────┼──────────────────────┼─────────────────────────────────────┤
│ 风险明细数据 │    智能体对话框       │ 结果辅助展示区                       │
│ (顶部区域)  │                      │  - 分析结果图表                      │
│             │                      │  - 生成的文件预览                    │
│ ┌─────────┐ │  ┌─────────────────┐ │  - 数据可视化                       │
│ │数据列表 │ │  │  对话框         │ │  - 任务详情弹窗                      │
│ │(表格)   │ │  │                │ │  - 其他辅助信息                      │
│ └─────────┘ │  │                │ │                                     │
│             │  │                │ │                                     │
│ 下发任务列表 │  │                │ │  [内容根据智能体交互动态显示]        │
│ (底部区域)  │  │                │ │                                     │
│             │  │                │ │                                     │
│ ┌─────────┐ │  │                │ │                                     │
│ │任务列表 │ │  │                │ │                                     │
│ │(卡片式) │ │  │                │ │                                     │
│ └─────────┘ │  └─────────────────┘ │                                     │
│             │                      │                                     │
│             │                      │                                     │
└─────────────┴──────────────────────┴─────────────────────────────────────┘
```

#### 左侧栏布局 (上下两栏)
1. **风险明细数据区域 (上方)**:
   - 显示所有上传或选择的风险明细数据
   - 表格形式展示，包含员工姓名、岗位、部门、员工ID、交易金额、交易时间、异常类型、风险等级
   - 支持排序、搜索、筛选功能
   - 可点击查看详细信息

2. **下发任务列表区域 (下方)**:
   - 显示已下发的任务列表
   - 卡片式布局，每个卡片显示任务ID、风险简述、创建时间、状态
   - 任务状态徽章（已创建、已下发、反馈完成、已超期）
   - 点击任务卡片可在右侧辅助区显示任务详情、反馈结果

#### 中间栏布局 (主要智能体对话框)
1. **智能体对话框**:
   - 支持文本输入和发送
   - 显示完整的对话历史，消息气泡样式（智能体左对齐，用户右对齐）
   - 时间戳和发送者信息
   - 支持文件上传和下载
   - 自动滚动到最新消息

#### 右侧栏布局 (结果辅助展示区)
1. **动态内容展示**:
   - 智能体生成的分析结果图表
   - 文件预览（PDF、图片等）
   - 数据可视化（表格、图表等）
   - 任务详情弹窗
   - 风险评估报告
   - 反馈总结展示

### 3.2 IM端智能体前端页面布局 (一线人员)

**布局结构**: 单栏聊天界面，类似微信聊天样式

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 风险核查助手 - 一线人员工作区                                              │
├─────────────────────────────────────────────────────────────────────────┤
│ 顶部栏: 显示当前对话状态 (如"风险核查中")                                   │
├─────────────────────────────────────────────────────────────────────────┤
│ 聊天区域 (占满大部分屏幕)                                                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ Agent: 您好，请核查以下员工信息。风险类型：交易异常。         │         │
│  │ 详见风险数据文件。请在24小时内提交核查结果。                  │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ 快递小哥: 收到，我已查看风险数据。会尽快完成核查。            │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ Agent: 感谢反馈。请上传核查结果文件。要求：1) 核查单需包含   │         │
│  │ 员工确认信息 2) 如有证明文件，请上传清晰的照片。               │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ 快递小哥: [文件上传] 核查单.pdf, 证明照片.jpg                 │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ 输入区域                                                               │
│ ┌─────────────────────────────────────────────────────────────┐        │
│ │ 消息输入框                                                  │        │
│ └─────────────────────────────────────────────────────────────┘        │
│ ┌──────┬───────────┐                                                  │
│ │ 发送 │  文件上传 │                                                  │
│ └──────┴───────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

**特点**:
- 无任务列表界面，所有信息都在对话中展现
- 智能体主动推送任务信息和风险数据
- 一线人员通过对话完成所有操作
- 对话中包含风险数据文件链接（可下载）
- 支持文本消息和文件上传
- 显示消息发送时间和已读状态

---

## 四、核心功能模块

### 4.1 业务负责人工作区 (WEB主智能体)

#### 系统prompt设计

**Web端智能体系统prompt**:
```
你是一个风险控制专家，负责协助业务负责人完成风险数据的分析、任务分派和反馈管理工作。

你的核心职责：
1. 帮助业务负责人分析上传的风险数据，识别风险特征和关键信息
2. 基于风险数据推荐合适的一线人员进行核查
3. 协助业务负责人完成任务的创建和分派
4. 回答业务负责人关于风险分析方法、任务管理流程的问题
5. 提供风险分析报告和建议

交互方式：
- 支持自然语言对话
- 可以分析上传的CSV文件内容
- 可以推荐合适的一线人员
- 可以创建风险任务
- 可以查看任务状态和反馈结果

风险数据分析要点：
- 识别异常交易模式
- 分析风险等级和影响范围
- 识别涉及的员工和部门
- 提供风险评估建议

任务分派规则：
- 根据风险数据中的员工部门信息匹配一线人员
- 考虑一线人员的工作负载和专业能力
- 确保任务分派的合理性和效率

请以专业、友好的语气与业务负责人对话，提供准确的分析和建议。
```

#### 核心功能

**功能1：风险数据分析和管理**

**业务流程**:
1. 业务负责人通过自然语言与智能体对话，要求分析风险数据
2. 智能体可以上传CSV文件，或查看预置的风险数据
3. 智能体根据统一的系统prompt分析数据并提供结果
4. 业务负责人可进行多轮对话，深入分析风险特征

**关键API**:
- `POST /api/upload-risk-data` - 上传风险数据文件
- `GET /api/sample-data` - 获取预置的风险数据列表
- `POST /api/chat` - 与智能体对话
  - 输入: 用户消息、上下文信息（包括已上传的风险数据）
  - 输出: 智能体回复、可能的操作建议

**前端交互**:
- 文件上传组件或下拉选择框
- 数据预览表格
- 智能体对话框（支持文本和文件交互）

**功能2：任务创建和管理**

**业务流程**:
1. 业务负责人通过对话要求创建风险任务
2. 智能体基于风险数据推荐合适的一线人员
3. 业务负责人确认或修改接收人后完成任务创建
4. 智能体帮助跟踪任务状态和反馈结果

**关键API**:
- `POST /api/chat` - 与智能体对话（任务创建请求）
- `POST /api/tasks` - 创建新任务（由智能体调用）
- `GET /api/tasks` - 获取任务列表（用于对话中的信息展示）

**前端交互**:
- 通过智能体对话框进行任务创建和管理
- 风险数据和任务信息在左侧栏显示

**关键逻辑**:
- 假设风险数据中的员工姓名唯一不重复
- AI基于员工的部门或其他特征识别推荐的接收人
- 如果无法匹配，系统提示"无合适接收人"

**前端交互**:
- 推荐结果展示（推荐人 + 推荐理由）
- "确认"按钮
- 修改接收人的下拉选择框（可选）

---

### 4.2 一线人员工作区 (IM模拟智能体)

#### 系统prompt设计

**IM端智能体系统prompt**:
```
你是一个风险核查助手，负责协助一线人员完成风险任务的核查工作。

你的核心职责：
1. 主动推送任务信息和风险数据给一线人员
2. 指导一线人员完成风险核查流程
3. 协助一线人员上传和验证核查文件
4. 回答一线人员关于风险任务的问题
5. 帮助一线人员完成任务提交和总结

交互方式：
- 支持自然语言对话
- 可以发送文件和接收文件
- 可以提供风险数据文件链接
- 可以验证文件内容和质量
- 可以生成反馈总结

风险核查要点：
- 确认风险数据的准确性
- 收集必要的证明文件
- 验证文件内容的完整性
- 评估风险的真实性和影响
- 提供风险处理建议

文件验证标准：
- 文件内容必须与风险任务相关
- 图片必须清晰可见，可识别关键信息
- 文档必须包含必要的签字或盖章
- 数据完整性和准确性检查

请以友好、专业的语气与一线人员对话，提供清晰的指导和支持。
```

#### 核心功能

**功能1：风险任务核查**

**业务流程**:
1. 一线人员进入工作区，直接与智能体开始对话
2. 智能体主动推送任务信息和风险数据链接
3. 一线人员通过对话了解任务要求和操作步骤
4. 智能体根据统一的系统prompt提供指导和建议

**关键API**:
- `POST /api/chat` - 与智能体对话
  - 输入: 用户消息、任务上下文信息
  - 输出: 智能体回复、可能的操作建议
- `GET /api/tasks?user_id=xxx&role=一线操作人员` - 获取当前用户的任务信息（在智能体对话中展示）
- `GET /api/tasks/{task_id}/chat-history` - 获取对话历史

**前端交互**:
- IM风格聊天界面（类似微信）
- 消息气泡样式（智能体左对齐，一线人员右对齐）
- 风险数据文件链接在对话中直接显示（可下载）
- 支持文本消息和文件上传

**功能2：文件上传和验证**

**业务流程**:
1. 一线人员通过对话要求上传文件
2. 智能体指导上传过程，并验证文件内容
3. 智能体基于系统prompt自动验证文件质量和内容
4. 如果文件不合格，智能体提供改进建议

**关键API**:
- `POST /api/chat` - 与智能体对话（文件上传请求）
- `POST /api/tasks/{task_id}/upload-file` - 上传文件（由智能体调用）
- `POST /api/tasks/{task_id}/verify-files` - 验证文件内容（由智能体调用）

**前端交互**:
- 文件上传按钮和文件列表显示
- 文件验证结果实时展示
- 支持重新上传功能

**功能3：任务提交和总结**

**业务流程**:
1. 一线人员完成所有核查工作后，通过对话要求提交任务
2. 智能体收集所有已上传的文件和对话记录
3. 智能体基于统一的系统prompt生成反馈总结
4. 完成任务状态更新和数据保存

**关键API**:
- `POST /api/chat` - 与智能体对话（任务提交请求）
- `POST /api/tasks/{task_id}/complete` - 完成任务（由智能体调用）

**前端交互**:
- 通过智能体对话框进行任务提交
- 任务完成后显示提示信息
4. 任务状态更新为"反馈完成"
5. 一线人员页面显示"任务已完成"提示

**关键API**:
- `POST /api/tasks/{task_id}/complete` - 完成任务并生成总结
  - 输入: task_id、chat_history、uploaded_files列表
  - 输出: feedback_summary、completion status

**前端交互**:
- "确认完成"按钮
- 完成后显示提示："任务已完成，反馈总结已生成"
- 可选：显示生成的反馈总结预览

---

## 五、智能体自由对话能力

### 5.1 对话系统架构

**Claude Code SDK 智能体框架**:
```
┌─────────────────────────────────────────┐
│          用户界面层 (Web/IM)            │
│  • 业务负责人工作区                     │
│  • 一线人员工作区                       │
└──────────────┬──────────────────────────┘
               │ REST API
┌──────────────▼──────────────────────────┐
│        后端服务层                      │
│  • Claude Code SDK 智能体实例化         │
│  • 系统prompt管理和加载                 │
│  • 对话状态跟踪和管理                   │
│  • 上下文信息处理                       │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│    Claude Code SDK 核心引擎             │
│  • 统一系统prompt执行                   │
│  • 多角色智能体管理                     │
│  • 上下文感知对话处理                   │
│  • 文件内容分析和验证                   │
│  • 任务流程引导和控制                   │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│        数据存储层                      │
│  • 用户信息和任务数据                   │
│  • 对话历史和文件存储                   │
│  • 风险数据和反馈记录                   │
└─────────────────────────────────────────┘
```

### 5.2 自由对话特性

**Web端智能体自由对话能力**:
- 支持自然语言对话，不受固定流程限制
- 可以主动提问关于风险数据的分析问题
- 可以要求查看任务状态和反馈结果
- 可以通过对话上传和管理风险数据
- 可以要求智能体创建和管理任务
- 支持多轮对话，保持对话上下文

**IM端智能体自由对话能力**:
- 支持自然语言对话，类似真实聊天体验
- 可以询问任务要求和操作步骤
- 可以请求上传和验证文件的帮助
- 可以讨论风险数据的细节
- 可以要求智能体提供指导和建议
- 支持多轮对话，保持对话上下文

### 5.3 统一对话API

**POST /api/chat - 智能体对话接口**

**请求格式**:
```json
{
  "user_id": "001",
  "role": "业务负责人",
  "message": "请分析这份风险数据的异常模式",
  "context": {
    "task_id": "TASK_001",
    "risk_data": "data/risk_data_001.csv",
    "chat_history": [
      {"role": "user", "content": "我需要分析一份风险数据"},
      {"role": "assistant", "content": "请上传风险数据文件"}
    ]
  }
}
```

**响应格式**:
```json
{
  "code": 0,
  "message": "成功",
  "data": {
    "response": "根据分析，这份风险数据显示出以下异常模式...",
    "suggested_actions": [
      {"type": "view_data", "label": "查看详细数据", "data": "data/risk_data_001.csv"},
      {"type": "create_task", "label": "创建风险任务", "data": {"task_summary": "快递员工异常交易识别"}}
    ],
    "context": {
      "new_task_id": "TASK_001"
    }
  }
}
```

### 5.4 对话状态管理

**状态跟踪**:
- 对话历史记录和上下文管理
- 任务状态和进度跟踪
- 用户角色和权限控制
- 风险数据和文件信息存储
- 智能体状态和策略调整

**状态转换**:
- 对话状态 -> 风险分析状态 -> 任务创建状态 -> 任务管理状态
- 风险任务状态 -> 文件上传状态 -> 文件验证状态 -> 任务完成状态

---

### 4.3 用户选择和页面导航

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
      "status": "反馈完成",
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
    "status": "反馈完成",
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
2. 调用Claude Code SDK，使用统一的Web端系统prompt进行分析
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
2. 调用Claude Code SDK，使用统一的Web端系统prompt推荐接收人
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
    "status": "反馈完成",
    "feedback_summary": "快递小哥已核查运单WLYD001的重量异常问题...",
    "summary_timestamp": "2025-02-28 10:35:00"
  }
}
```

**后端逻辑**:
1. 获取完整的对话历史（从内存/临时存储中）
2. 获取所有上传的文件列表和验证结果
3. 调用Claude API生成反馈总结
4. 将对话历史、文件列表、反馈总结保存到feedback JSON文件
5. 更新tasks.csv中的任务状态为"反馈完成"和完成时间
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
- [ ] 已下发任务列表
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

## 六、技术栈选型（已确定）

### 后端技术栈
- **Python 3.10+**
- **FastAPI** - 现代、高性能异步Web框架
  - 自动API文档生成 (Swagger/OpenAPI)
  - 原生异步支持 (async/await)
  - 类型提示支持 (Pydantic)
  - CORS中间件支持
- **Agent SDK** - 智能体服务集成
  - ManagerAgent - 业务负责人智能体
  - StaffAgent - 一线人员智能体
  - SessionManager - 会话状态管理

### 前端技术栈
- **React 18** - 现代React版本，支持并发特性
- **Vite** - 下一代前端构建工具
  - 快速冷启动
  - 即时热更新 (HMR)
  - 优化的生产构建
- **CSS Modules** - 组件级样式隔离

### 开发环境
- **Node.js 18+** (前端)
- **Python 3.10+** (后端)
- **Uvicorn** - ASGI服务器，用于运行FastAPI
- **CORS配置** - 支持跨域请求 (开发环境)

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

### 8.1 Claude Agent SDK 集成（推荐方案）

**重要更新（2026-03-03）**：本项目采用 Claude Agent SDK 而非直接调用 Anthropic API，以支持更强大的智能体能力。

#### 8.1.1 SDK 说明

项目已包含参考实现：`claude_agent_demo.py`

**核心优势**：
- 支持 MCP（Model Context Protocol）工具扩展
- 支持多轮对话和上下文管理
- 支持自定义 System Prompt
- 支持工具调用（Function Calling）

#### 8.1.2 依赖安装

```bash
pip install claude-agent-sdk python-dotenv
```

#### 8.1.3 环境配置

本项目使用本机已安装的 Claude Code 配置（从 `~/.claude.json` 提取）：

**配置信息：**
| 参数 | 值 |
|------|-----|
| ANTHROPIC_BASE_URL | https://ark.cn-beijing.volces.com/api/coding |
| ANTHROPIC_AUTH_TOKEN | 004082f8-6dd5-49d5-9132-afe3f63e5ce2 |
| ANTHROPIC_MODEL | ark-code-latest |

在项目根目录创建 `.env` 文件：

```env
# 火山引擎方舟 Claude Code 配置
ANTHROPIC_BASE_URL=https://ark.cn-beijing.volces.com/api/coding
ANTHROPIC_AUTH_TOKEN=004082f8-6dd5-49d5-9132-afe3f63e5ce2
ANTHROPIC_MODEL=ark-code-latest

# 禁用非必要流量
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

> 📌 **注意**：本配置与本机 Claude Code 共用相同的 API，无需额外申请。

#### 8.1.4 智能体架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI 后端服务                      │
├─────────────────────────────────────────────────────────┤
│  API 层                                                  │
│  ├── GET  /api/users (用户列表)                         │
│  ├── GET  /api/users/{id} (单个用户)                    │
│  ├── GET  /api/tasks (任务列表)                         │
│  ├── POST /api/tasks (创建任务)                         │
│  ├── GET  /api/tasks/{id} (任务详情)                    │
│  ├── POST /api/chat (业务负责人对话)                    │
│  └── POST /api/agent-chat (一线人员智能体对话)          │
├─────────────────────────────────────────────────────────┤
│  智能体层 (Claude Agent SDK)                            │
│  ┌─────────────────┐    ┌─────────────────┐           │
│  │ Web端智能体      │    │ IM端智能体       │           │
│  │ (Manager Agent) │    │ (Staff Agent)   │           │
│  └────────┬────────┘    └────────┬────────┘           │
│           │                       │                     │
│  ┌───────┴───────────────────────┴───────┐              │
│  │        System Prompt 设计             │              │
│  │  • 角色定义                          │              │
│  │  • 工具能力说明                     │              │
│  │  • 业务规则                         │              │
│  └─────────────────────────────────────┘              │
├─────────────────────────────────────────────────────────┤
│  工具层 (Tool Functions)                                │
│  ├── 查询风险数据 (read_risk_data)                      │
│  ├── 创建任务 (create_task)                             │
│  ├── 查询任务状态 (get_task_status)                     │
│  ├── 上传文件 (upload_file)                            │
│  └── 发送消息 (send_message)                           │
└─────────────────────────────────────────────────────────┘

#### 8.1.5.1 文档解析工具（重要！）

由于Claude Agent本身是文本模型，无法直接读取PDF/Word/Excel，需要通过解析工具将文档转换为文本后再进行分析。

| 工具 | 依赖库 | 功能 |
|------|--------|------|
| parse_csv | pandas | 解析CSV文件为DataFrame |
| parse_excel | pandas, openpyxl | 解析Excel文件 |
| parse_pdf | PyPDF2, pdfplumber | 解析PDF文件提取文本 |
| parse_word | python-docx | 解析Word文件提取文本 |

**工作流程**：
```
用户上传文件 → 解析工具转文本 → Agent分析 → 返回结果
```
```

#### 8.1.5 System Prompt 设计

**Web端智能体（业务负责人）**：
```
你是一个风险控制专家Agent，负责协助业务负责人完成风险数据的分析、任务分派和反馈管理工作。

你的核心职责：
1. 帮助业务负责人分析上传的风险数据，识别风险特征和关键信息
2. 基于风险数据推荐合适的一线人员进行核查
3. 协助业务负责人完成任务的创建和分派
4. 回答业务负责人关于风险分析方法、任务管理流程的问题
5. 提供风险分析报告和建议

可用工具：
- parse_csv: 解析CSV风险数据文件
- parse_excel: 解析Excel风险数据文件
- parse_pdf: 解析PDF文档
- parse_word: 解析Word文档
- read_risk_data: 读取风险数据CSV文件
- create_task: 创建新的风险核查任务
- get_task_status: 查询任务状态和反馈结果
- list_users: 列出可用的执行人员

请以专业、友好的语气与业务负责人对话，提供准确的分析和建议。
```

**IM端智能体（一线人员）**：
```
你是一个风险核查助手Agent，负责协助一线人员完成风险任务的核查工作。

你的核心职责：
1. 主动推送任务信息和风险数据给一线人员
2. 指导一线人员完成风险核查流程
3. 协助一线人员上传和验证核查文件
4. 回答一线人员关于风险任务的问题
5. 帮助一线人员完成任务提交和总结

可用工具：
- parse_pdf: 解析PDF证明文件
- parse_word: 解析Word证明文件
- parse_image: 解析图片文件（通过OCR）
- get_task_detail: 获取当前任务详情和风险数据
- upload_file: 上传核查证明文件
- verify_file: 验证上传文件是否符合要求
- complete_task: 完成任务并生成反馈总结

请以友好、专业的语气与一线人员对话，提供清晰的指导和支持。
```

#### 8.1.6 代码实现示例

**初始化智能体客户端**：
```python
import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from dotenv import load_dotenv
import os

load_dotenv()

def build_agent_options(system_prompt: str) -> ClaudeAgentOptions:
    """构建智能体选项"""
    return ClaudeAgentOptions(
        env={
            "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL"),
            "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN"),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
        },
        # 注入自定义 System Prompt
        prompt=system_prompt,
        # 权限模式
        permission_mode="acceptEdits",
        # 最大对话轮次
        max_turns=10,
        thinking={"type": "disabled"}
    )

# 管理智能体实例（全局/单例）
manager_agent_client = None
staff_agent_client = None
```

**处理对话请求**：
```python
async def chat_with_agent(user_message: str, context: dict):
    """与智能体对话"""
    global manager_agent_client
    
    if manager_agent_client is None:
        options = build_agent_options(MANAGER_SYSTEM_PROMPT)
        manager_agent_client = ClaudeSDKClient(options=options)
        await manager_agent_client.__aenter__()
    
    # 构建上下文消息
    prompt = f"""
    当前用户：{context.get('username')} ({context.get('role')})
    任务ID：{context.get('task_id', '无')}
    
    用户消息：{user_message}
    """
    
    await manager_agent_client.query(prompt)
    
    # 收集回复
    responses = []
    async for msg in manager_agent_client.receive_response():
        responses.append(msg)
    
    return process_agent_responses(responses)
```

#### 8.1.7 工具函数注册

```python
from claude_agent_sdk import function

@function
def read_risk_data(file_path: str) -> str:
    """读取风险数据文件"""
    # 实现代码
    pass

@function
def create_task(task_info: dict) -> dict:
    """创建新任务"""
    # 实现代码
    pass

@function
def get_task_status(task_id: str) -> dict:
    """查询任务状态"""
    # 实现代码
    pass

@function
def upload_file(task_id: str, file_data: bytes) -> dict:
    """上传文件"""
    # 实现代码
    pass

# 注册工具
AGENT_TOOLS = [
    read_risk_data,
    create_task,
    get_task_status,
    upload_file,
]
```

---

### 8.2 Claude API集成（备选方案）

> ⚠️ **注意**：以下为备选方案，仅在 Claude Agent SDK 无法满足需求时使用。

**需要集成的4个场景**:
1. **风险数据分析** (POST /api/analyze)
2. **推荐接收人** (POST /api/recommend-receiver)
3. **文件内容验证** (POST /api/tasks/{task_id}/verify-files)
4. **反馈总结生成** (POST /api/tasks/{task_id}/complete)

**API调用方式** (以Python FastAPI为例):
```python
from fastapi import FastAPI, HTTPException
from anthropic import Anthropic
import os

app = FastAPI()
client = Anthropic()

@app.post("/api/analyze-risk")
async def analyze_risk_data(request: dict):
    try:
        risk_data_content = request.get("risk_data")
        user_message = request.get("message")
        
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
- [ ] 任务状态更新为"反馈完成"
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

## 📋 当前实现状态 (2026-03-03)

### 已完成 ✅
- [x] 用户列表展示
- [x] 任务列表展示
- [x] 基础三栏布局（用户列表/任务列表 + 对话 + 详情）
- [x] 创建任务弹窗
- [x] 用户选择界面（支持URL参数 user_id=xxx）
- [x] 区分业务负责人和一线人员的界面
- [x] 业务负责人：风险数据展示
- [x] 一线人员：IM风格聊天界面（已优化为纯对话，无任务列表）
- [x] 一线人员：文件上传功能
- [x] 基础对话功能（伪智能体 - 关键词匹配）

### 待完善 🔧
- [ ] **修复任务对话数据混乱问题（重要！）**
  - [ ] Web端和IM端对话数据需要分开存储
  - [ ] Web端：任务创建对话（业务负责人 ↔ 智能体）
  - [ ] IM端：任务执行对话（一线人员 ↔ 智能体）
- [ ] **接入 Claude Agent SDK（核心任务）**
  - [ ] 安装 claude-agent-sdk 依赖
  - [ ] 配置 API 环境和 .env 文件
  - [ ] 实现 Web端智能体（Manager Agent）
  - [ ] 实现 IM端智能体（Staff Agent）
  - [ ] 设计 System Prompt
  - [ ] 注册工具函数（风险数据查询、任务管理等）
- [ ] 风险数据上传功能
- [ ] 数据分析结果展示
- [ ] 反馈总结展示
- [ ] 页面标题优化：将"大件风控系统"改为"风控数字员工"
- [ ] 风险数据区域优化：添加翻页功能，减少高度，支持与下发任务区域之间的高度自由调节

### 🔴 严重问题修复

#### 问题描述（2026-03-03 更新）

**问题现象**：点击任务卡片后，Web端显示了IM端一线人员的对话内容

**问题根源**：
- 当前所有对话历史都存储在 `feedback/{task_id}.json` 文件中
- Web端（业务负责人）和IM端（一线人员）共用同一个存储
- 导致业务负责人点击任务时，看到的是一线人员的对话记录

**正确的数据流设计**：

```
┌──────────────────────────────────────────────────────────────┐
│                    任务全生命周期                              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  【阶段1：任务创建】← Web端智能体处理                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 业务负责人 → 智能体：分析风险数据                      │    │
│  │ 智能体 → 业务负责人：推荐执行人                        │    │
│  │ 业务负责人 → 智能体：确认创建任务                      │    │
│  │ 智能体 → 业务负责人：任务创建成功                      │    │
│  └─────────────────────────────────────────────────────┘    │
│  存储位置：task_creation/{task_id}_creation.json           │
│                                                               │
│  【阶段2：任务执行】← IM端智能体处理                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 智能体 → 一线人员：推送任务信息                        │    │
│  │ 一线人员 → 智能体：回复核查情况                        │    │
│  │ 一线人员 → 智能体：上传证明材料                        │    │
│  │ 智能体 → 一线人员：确认完成                            │    │
│  └─────────────────────────────────────────────────────┘    │
│  存储位置：feedback/{task_id}.json                         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Web端（业务负责人）应该看到的**：
- 任务创建时的对话记录（分析→推荐→确认→下发）
- 任务创建成功后可以在右侧查看"任务详情"
- 不应该看到一线人员的执行对话

**IM端（一线人员）应该看到的**：
- 自己接收到的任务推送
- 与智能体的核查对话
- 上传文件的记录
- 任务完成状态

### 智能体接入计划 📋

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| Phase 1 | 环境配置 + SDK集成 | P0 |
| Phase 2 | Web端智能体实现 | P0 |
| Phase 3 | IM端智能体实现 | P0 |
| Phase 4 | 工具函数注册 | P1 |
| Phase 5 | 对话测试和调优 | P1 |

### 问题修复 🐛
- [x] ~~前端启动命令~~ (已修复，需用python3)
- [x] ~~伪智能体~~ (计划接入真智能体)
- [ ] 风控数据API文件路径问题 (当前返回空数据)
