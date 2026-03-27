# 待办项系统 (To-Do Items Feature) - 完整设计文档

**文档版本**: 1.0
**更新日期**: 2026-03-26
**所有权**: DJAgent 项目

---

## 目录

1. [需求概述](#1-需求概述)
2. [页面设计](#2-页面设计)
3. [设计系统](#3-设计系统)
4. [数据结构](#4-数据结构)
5. [API 设计](#5-api-设计)
6. [待办项分类](#6-待办项分类)
7. [交互流程](#7-交互流程)
8. [Mock 数据示例](#8-mock-数据示例)
9. [实现指南](#9-实现指南)
10. [文件清单](#10-文件清单)

---

## 1. 需求概述

### 1.1 核心功能

将 Manager Agent 从**被动应答** 升级至**主动扫描**，通过自动化规则识别风险、任务、异常问题，形成系统化的待办项，供业务经理快速处理。

**Demo 阶段**：待办项通过 Mock 数据展示（不实现 Agent 自动扫描）。

### 1.2 三大自动扫描能力（Phase 3）

| 扫描类型 | 触发方式 | 输出结果 | 优先级 |
|---------|--------|--------|------|
| **风险数据问题** | 定时扫描 + 事件触发 | P0-P3 待办项 | 高 |
| **任务问题** | 事件触发（任务超期/不合理等） | P0-P3 待办项 | 高 |
| **异常问题** | 系统异常检测 | P1-P3 待办项 | 中 |

### 1.3 规则系统（Phase 3 后续）

**管理员预置规则** (对所有用户统一适用)
- 风险数据异常检测（如跨度过大、缺数据）
- 任务逾期检测
- 地区风险评分阈值检测

**用户自定义规则** (仅对当前用户生效)
- 关键指标监控范围
- 自定义时间提醒
- 特定地区或人员的关注规则

### 1.4 目标用户

- **Manager（业务负责人）**: 在 Web 端查看、处理待办项
- 支持**地区切换**（HQ 可切换，Local 只见自己地区）

---

## 2. 页面设计

### 2.1 整体布局（Web 3 栏式布局）

```
┌──────────────────────────────────────────────────────────────────┐
│                         Header（顶部导航）                         │
├──────────────────────────────────────────────────────────────────┤
│           │                                    │                  │
│  Left     │                                    │   Right          │
│  Sidebar  │         Main Chat Area             │   Detail Panel   │
│ (Tabs)    │        (对话界面)                  │   (详情展示)      │
│           │                                    │                  │
│ ┌──────┐  │  ┌──────────────────────────┐    │ ┌──────────────┐ │
│ │ 📋   │  │  │   Agent 回复消息          │    │ │ 待办项详情    │ │
│ │ 今日 │  │  │   长篇幅内容...          │    │ │              │ │
│ │ 待办 │  │  │                          │    │ │ 标题: ...     │ │
│ │      │  │  ├──────────────────────────┤    │ │ 优先级: P0    │ │
│ │ ──── │  │  │   对话输入框              │    │ │ 推荐执行人: 王 │ │
│ │ 📊   │  │  │ [输入消息...]  [发送]    │    │ │             │ │
│ │ 风险 │  │  │                          │    │ │ [查看详情▼]   │ │
│ │ 数据 │  │  │                          │    │ │              │ │
│ │      │  │  │                          │    │ │ [一键下发]   │ │
│ │ ──── │  │  │                          │    │ │              │ │
│ │ ✓    │  │  │                          │    │ │              │ │
│ │ 任务 │  │  │                          │    │ │              │ │
│ │ 追踪 │  │  │                          │    │ │              │ │
│ │      │  │  │                          │    │ │              │ │
│ └──────┘  │  └──────────────────────────┘    │ └──────────────┘ │
│           │                                    │                  │
│  [卡片1]  │                                    │                  │
│  [卡片2]  │                                    │                  │
│  [卡片3]  │                                    │                  │
│           │                                    │                  │
└──────────────────────────────────────────────────────────────────┘
```

**布局结构说明**:
- **左栏（左 Sidebar，~300px，可折叠）**:
  - **顶部控制区**：
    - 3 个 Tab 按钮（今日待办 / 风险数据 / 任务追踪）
    - 右侧：折叠按钮（< 符号），点击可隐藏左栏
  - **独立的展开/折叠控制**，与当前 Tab 无关
  - **折叠时**：左栏完全隐藏，中栏和右栏自动扩展占满空间
  - **展开时**：左栏恢复 ~300px 宽度，显示当前选中 Tab 的内容
  - **折叠/展开状态独立维护**：切换 Tab 时，左栏状态保持不变
  - **内容**：根据选中的 Tab 显示对应列表
    - Tab 1「今日待办」：待办项卡片列表（分组显示）
    - Tab 2「风险数据」：风险数据表格（与现在完全相同）
    - Tab 3「任务追踪」：任务列表（与现在完全相同）

- **中栏（主对话界面，自适应）**:
  - **保持完全不变**，继续显示 Agent 与用户的对话历史
  - 对话输入框在底部
  - 支持将左栏「今日待办」的待办项添加到对话中
  - **宽度自适应**：当左栏折叠时，中栏宽度自动扩展

- **右栏（右详情面板，~350px，可折叠）**:
  - **独立的展开/折叠控制**，与当前 Tab 无关
  - **展开时**：根据当前交互对象自动显示详情
    - 点击待办项卡片 → 自动弹出展示该待办项完整详情（标题、优先级、推荐执行人、一键下发按钮等）
    - 点击任务卡片 → 自动弹出展示该任务完整信息（标题、执行人、进度、截止时间等）
  - **折叠时**：右栏完全隐藏，中栏自动扩展
  - **折叠/展开状态独立维护**：点击其他 Tab 时不会自动折叠，保持用户最后的状态
  - **手动控制**：用户可随时点击关闭按钮手动折叠右栏

### 2.2 三个 Tab 页面详细设计

#### **Tab 1: 今日待办 (默认打开)**

**内容**: 按优先级 P0→P3 排序的待办项

**分组结构**:
1. 运单数据问题 (展开)
   - 根据风险类型 (虚假刷单/后补单/运费异常/货物损坏/虚假签收/时间异常/重量异常) 分类
   - 每个类型内按优先级排序

2. 任务问题 (展开)
   - 根据问题类型 (超期/未更新/进度缓慢/分配不当) 分类
   - 每个类型内按优先级排序

3. 异常问题 (展开)
   - 业务执行和运营层面的异常 (执行人绩效/地区风险/客户供应商/流程效率)

**待办卡片字段**:
```
┌───────────────────────────────────────────┐
│ 优先级 P0  | 类型: 运费异常               │
├───────────────────────────────────────────┤
│ 标题: "运单WLYD5678298结算异常 - 高风险"   │
│ 描述: "运费800元 vs 结算3617元，差异452%" │
│ 关键数据: 异常幅度: 2817元 | 货物: 电子产品 │
│ 推荐执行人: 刘伟 (自动推荐)              │
├───────────────────────────────────────────┤
│ 发现时间: 2026-03-26 09:30                │
│ 状态: 未处理  | [查看详情→]               │
└───────────────────────────────────────────┘
```

**右侧详情面板** - 显示完整待办详情:
- 问题背景 + 原始数据表格
- 分析结果 (变化趋势、影响范围)
- **推荐执行人** (关键字段，仅右侧显示)
- 预期处理时间
- **一键下发按钮** (触发执行流程)
- 相关任务关联

---

#### **Tab 2: 风险数据**

**左栏显示内容**：直接复用当前 App 左侧栏上半部分的风险数据表格/列表

**说明**:
- 功能**完全保持不变**，与现在的表现形式一致
- 仅做布局调整：占满整个左栏高度（移除上下分割线）
- 支持日度/月度切换、排序、筛选等现有功能

**与右栏的关系**: **无直接关联，但右栏可独立存在**
- 右栏展开/折叠状态独立维护，不因切换到风险数据 Tab 而自动折叠
- 如果此前在「今日待办」或「任务追踪」中打开了右栏，切换到风险数据 Tab 时右栏保持展开状态（显示之前的内容）
- 风险数据表格与右栏内容无交互关系
- 选择数据行后，仅支持添加到中栏对话框（现有功能）

---

#### **Tab 3: 任务追踪**

**左栏显示内容**：直接复用当前 App 左侧栏下半部分的任务列表

**说明**:
- 功能**完全保持不变**，与现在的表现形式一致
- 仅做布局调整：占满整个左栏高度（移除上下分割线）
- 支持任务筛选、排序、状态显示等现有功能
- 一键下发创建的任务会自动出现在此列表中

**与右栏的关系**: **有交互关联**
- 点击左栏任务卡片 → 右栏自动弹出显示该任务的完整详情
- 右栏显示内容：任务标题、描述、优先级、创建者、执行人、进度、截止时间等
- 支持在右栏进行任务状态更新
- 显示相关的待办项信息（如该任务来源于哪个待办项）
- 右栏展开状态独立维护，切换 Tab 时保持当前展开/折叠状态

---

### 2.3 中栏对话区域（保持现有布局）

**位置**: 中栏对话界面（保持现有布局和功能）

**特性**:
- 继续显示 Agent 与用户的对话历史
- 对话输入框保持在下方
- 支持将左栏的待办项添加到聊天（转为文本描述）
- 可包含代码块、表格等复杂内容
- Agent 回复可包含待办项修改建议

**与待办的互动流程**:
1. Manager 在左栏「今日待办」看到推荐执行人不满意
2. 点击待办卡片的"添加到对话"按钮
3. 待办项转为文本添加到中栏聊天
4. Manager: "这个任务应该由李经理执行"
5. Agent: 在中栏回复修改建议
6. Manager 返回左栏「今日待办」，手动刷新查看更新（Demo 阶段）
7. 确认无误后点击待办卡片的"一键下发"按钮

---

## 3. 设计系统

### 3.1 CSS 变量 (来自 App.css)

```css
:root {
  /* 统一主色调 - 蓝色系 */
  --primary-color: #1890ff;
  --primary-dark: #096dd9;
  --primary-light: #e6f7ff;

  /* 状态色 */
  --success-color: #52c41a;      /* 绿色 - 已处理/成功 */
  --warning-color: #faad14;      /* 橙色 - 警告/待处理 */
  --danger-color: #ff4d4f;       /* 红色 - 紧急/失败 */

  /* 文字色 */
  --text-primary: #262626;
  --text-secondary: #8c8c8c;
  --text-disabled: #bfbfbf;

  /* 背景色 */
  --bg-gray: #f5f5f5;
  --bg-white: #ffffff;
  --bg-primary-light: #e6f7ff;

  /* 边框色 */
  --border-color: #e8e8e8;
  --border-focus: var(--primary-color);

  /* 间距 - 统一为 8px 基准网格 */
  --spacing-xs: 4px;   /* 4px */
  --spacing-sm: 8px;   /* 8px */
  --spacing-md: 16px;  /* 16px */
  --spacing-lg: 24px;  /* 24px */
  --spacing-xl: 32px;  /* 32px */

  /* 圆角 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;

  /* 阴影 */
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.12);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.16);
}
```

### 3.2 排版规范

| 用途 | 字体大小 | 字重 | 颜色 | 行高 |
|-----|--------|------|-----|------|
| 页面标题 | 18px | 600 | --text-primary | 1.4 |
| 卡片标题 | 16px | 600 | --text-primary | 1.4 |
| 段落正文 | 14px | 400 | --text-primary | 1.6 |
| 次级文本 | 12px | 400 | --text-secondary | 1.5 |
| 标签/标记 | 12px | 500 | --text-secondary | 1.4 |
| 时间戳 | 11px | 400 | --text-disabled | 1.4 |

### 3.3 优先级 Badge 样式

| 优先级 | 背景色 | 文字色 | 圆角 | 使用场景 |
|------|------|------|------|---------|
| **P0** | #ff4d4f | white | 4px | 紧急，需立即处理 |
| **P1** | #faad14 | white | 4px | 高优先级 |
| **P2** | #1890ff | white | 4px | 中等优先级 |
| **P3** | #8c8c8c | white | 4px | 低优先级 |

### 3.4 待办项状态样式

| 状态 | 卡片背景 | 文字色 | 边框 | 整体样式 |
|-----|--------|------|------|---------|
| **未处理** | #ffffff | --text-primary | 1px --border-color | 正常 |
| **已处理** | #f5f5f5 | --text-disabled | 1px --border-color | 灰显 + opacity 0.6 |

### 3.5 按钮规范

```css
/* 主按钮 - 一键下发 */
.btn-primary {
  background: var(--primary-color);
  color: white;
  padding: var(--spacing-sm) var(--spacing-md);  /* 8px 16px */
  border-radius: var(--radius-sm);               /* 8px */
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: var(--primary-dark);
  box-shadow: var(--shadow-md);
}

.btn-primary:active {
  transform: translateY(1px);
  box-shadow: var(--shadow-sm);
}

.btn-primary:disabled {
  background: var(--text-disabled);
  cursor: not-allowed;
  opacity: 0.5;
}

/* 次级按钮 - 查看详情 */
.btn-secondary {
  background: transparent;
  color: var(--primary-color);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  border-color: var(--primary-color);
  background: var(--primary-light);
}

/* 危险按钮 - 删除/拒绝 */
.btn-danger {
  background: var(--danger-color);
  color: white;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  border: none;
  cursor: pointer;
}

.btn-danger:hover {
  background: #ff7875;
}
```

### 3.6 卡片通用样式

```css
.card {
  background: var(--bg-white);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);          /* 12px */
  padding: var(--spacing-md);               /* 16px */
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--primary-color);
}

.card.processed {
  opacity: 0.6;
  background: var(--bg-gray);
}

.card.priority-p0 {
  border-left: 4px solid var(--danger-color);
}

.card.priority-p1 {
  border-left: 4px solid var(--warning-color);
}

.card.priority-p2 {
  border-left: 4px solid var(--primary-color);
}

.card.priority-p3 {
  border-left: 4px solid var(--text-disabled);
}
```

---

## 4. 数据结构

### 4.1 待办项 (TodoItem) JSON Schema

```json
{
  "id": "TODO-2026-001",
  "title": "华南地区昨日进出口跨度异常",
  "description": "跨度 500%，超过阈值",
  "category": "风险数据问题",
  "type": "跨度异常",
  "priority": "P0",
  "status": "未处理",
  "severity": "critical",

  "source_data": {
    "date": "2026-03-25",
    "region": "华南",
    "metrics": {
      "import": 10000,
      "export": 15000,
      "span_percentage": 150
    }
  },

  "analysis": {
    "trend": "上升趋势明显",
    "change_rate": "150%",
    "affected_items": 5,
    "root_cause": "出口订单增加，进口原料减少"
  },

  "recommended_assignee": {
    "user_id": "user_002",
    "name": "王经理",
    "reason": "华南地区负责人，具有数据核查权限"
  },

  "expected_handling_time": {
    "start_date": "2026-03-26",
    "due_date": "2026-03-27",
    "priority_hours": 24
  },

  "metadata": {
    "created_at": "2026-03-26T09:30:00Z",
    "created_by": "system",
    "updated_at": "2026-03-26T09:30:00Z",
    "related_task_ids": ["TASK-2026-001"],
    "related_chat_messages": ["msg_123"]
  }
}
```

### 4.2 分组结构 (TodoGroup)

```json
{
  "id": "group_风险数据问题_P0",
  "name": "风险数据问题",
  "priority": "P0",
  "expanded": true,
  "items": [
    { "id": "TODO-2026-001", ... },
    { "id": "TODO-2026-002", ... }
  ],
  "item_count": 2,
  "processed_count": 0,
  "sub_groups": {
    "跨度异常": [
      { "id": "TODO-2026-001", ... }
    ],
    "缺数据": [
      { "id": "TODO-2026-002", ... }
    ]
  }
}
```

### 4.3 任务 (Task) - 由待办项下发生成

```json
{
  "id": "TASK-2026-001",
  "title": "华南地区风险数据异常核查",
  "description": "请核查华南地区进出口数据的跨度异常问题",
  "priority": "P0",
  "status": "进行中",

  "creator": {
    "user_id": "user_001",
    "name": "张总经理"
  },

  "assigned_to": {
    "user_id": "user_002",
    "name": "王经理"
  },

  "source": {
    "type": "待办项下发",
    "todo_id": "TODO-2026-001"
  },

  "deadline": "2026-03-27T17:00:00Z",
  "created_at": "2026-03-26T09:35:00Z",
  "updated_at": "2026-03-26T09:35:00Z",

  "progress": {
    "percentage": 30,
    "last_updated": "2026-03-26T14:00:00Z"
  },

  "related_data": {
    "risk_data_id": "risk_data_001",
    "documents": []
  },

  "metadata": {
    "attachments": [],
    "tags": ["风险数据", "华南", "紧急"]
  }
}
```

### 4.4 右侧详情面板数据 (DetailPanel)

```json
{
  "type": "todo_detail" | "task_detail" | "risk_data_detail",

  "content": {
    /* 根据 type 显示不同内容 */
  },

  "actions": {
    /* 根据 type 显示不同按钮 */
  }
}
```

---

## 5. API 设计

### 5.1 待办项相关 API

#### **GET /api/todos/today**

获取今日待办项列表

**查询参数**:
```
?priority=P0,P1  (可选，按优先级筛选)
?category=风险数据问题,任务问题  (可选)
?status=未处理,已处理  (可选)
?region=华南  (可选，地区筛选)
```

**响应**:
```json
{
  "success": true,
  "data": {
    "groups": [
      {
        "id": "group_风险数据问题",
        "name": "风险数据问题",
        "items": [
          {
            "id": "TODO-2026-001",
            "title": "华南地区昨日进出口跨度异常",
            "priority": "P0",
            "status": "未处理",
            ...
          }
        ]
      }
    ],
    "total_count": 10,
    "unprocessed_count": 8
  }
}
```

#### **GET /api/todos/{id}**

获取单个待办项详情

**路径参数**:
- `id`: 待办项 ID

**响应**:
```json
{
  "success": true,
  "data": {
    "id": "TODO-2026-001",
    "title": "华南地区昨日进出口跨度异常",
    "description": "...",
    "recommended_assignee": { ... },
    "expected_handling_time": { ... },
    ...
  }
}
```

#### **GET /api/todos/{id}/preview**

获取待办项下发预览（一键下发前的确认信息）

**路径参数**:
- `id`: 待办项 ID

**响应**:
```json
{
  "success": true,
  "data": {
    "title": "华南地区风险数据异常核查",
    "priority": "P0",
    "assigned_to": {
      "user_id": "user_002",
      "name": "王经理"
    },
    "deadline": "2026-03-27T17:00:00Z",
    "data_summary": "进出口数据对比表",
    "expected_effort": "1-2小时"
  }
}
```

#### **POST /api/todos/{id}/execute**

执行待办项（一键下发），创建关联任务

**路径参数**:
- `id`: 待办项 ID

**请求体**:
```json
{
  "confirmation": true,
  "assigned_to_user_id": "user_002",
  "deadline_offset_hours": 24,
  "custom_description": "附加说明（可选）"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "todo_id": "TODO-2026-001",
    "task_id": "TASK-2026-001",
    "status": "已下发",
    "created_at": "2026-03-26T09:35:00Z"
  }
}
```

#### **PATCH /api/todos/{id}**

更新待办项状态或内容

**路径参数**:
- `id`: 待办项 ID

**请求体**:
```json
{
  "status": "已处理" | "未处理",
  "priority": "P0" | "P1" | "P2" | "P3",
  "recommended_assignee": { ... },
  "notes": "备注信息"
}
```

**响应**:
```json
{
  "success": true,
  "data": { ... }
}
```

#### **POST /api/todos/{id}/add-to-chat**

将待办项添加到聊天（转为文本）

**路径参数**:
- `id`: 待办项 ID

**响应**:
```json
{
  "success": true,
  "data": {
    "message_id": "msg_123",
    "text": "待办项 #TODO-2026-001: 华南地区昨日进出口跨度异常...",
    "added_at": "2026-03-26T10:00:00Z"
  }
}
```

### 5.2 任务相关 API

#### **GET /api/tasks**

获取任务列表，支持按状态筛选

**查询参数**:
```
?status=进行中,已完成,逾期  (可选)
?assigned_to=user_002  (可选)
?source=待办项下发  (可选)
?priority=P0,P1  (可选)
```

**响应**:
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "id": "TASK-2026-001",
        "title": "华南地区风险数据异常核查",
        "status": "进行中",
        "priority": "P0",
        "assigned_to": { ... },
        "deadline": "2026-03-27T17:00:00Z",
        "progress": 30
      }
    ],
    "total": 15,
    "in_progress": 8,
    "completed": 5,
    "overdue": 2
  }
}
```

#### **GET /api/tasks/{id}**

获取单个任务详情

**路径参数**:
- `id`: 任务 ID

**响应**: 返回完整的任务对象

#### **PATCH /api/tasks/{id}**

更新任务状态

**请求体**:
```json
{
  "status": "进行中" | "已完成" | "已取消",
  "progress": 50,
  "notes": "更新说明"
}
```

### 5.3 风险数据 API

#### **GET /api/risk-data**

获取风险数据列表，支持日度/月度切换

**查询参数**:
```
?date=2026-03-26  (可选，日期筛选)
?type=daily | monthly  (必填)
?region=华南  (可选)
```

**响应**:
```json
{
  "success": true,
  "data": {
    "type": "daily",
    "date": "2026-03-26",
    "rows": [
      {
        "id": "risk_data_001",
        "region": "华南",
        "metrics": { ... },
        "has_todo": true,
        "todo_id": "TODO-2026-001"
      }
    ]
  }
}
```

#### **GET /api/risk-data/{id}**

获取单条风险数据详情及相关待办项

**响应**:
```json
{
  "success": true,
  "data": {
    "risk_data": { ... },
    "related_todos": [ ... ],
    "analysis": { ... }
  }
}
```

---

## 6. 待办项分类

### 6.1 运单数据问题

针对运单数据异常的待办项。包括运单本身的各类风险（虚假刷单、后补单、运费异常等）需要核查。

| 类型 | 判断标准 | 优先级 | 推荐处理 |
|-----|--------|------|--------|
| **虚假刷单** | 检测到订单数据异常（如流程跳步、多次重复提交、异常地点），判定为虚假交易 | P0-P1 | 立即冻结账户，调查刷单来源，追回结算款项 |
| **后补单** | 运单创建时间过晚（相对于发货时间），或订单数据不完整后补充 | P0-P1 | 核实货物实际发货时间和收货状态，判断是否真实交易 |
| **运费异常** | 运费与结算金额差异超过阈值（如 >20%）、异常大，或存在异常折扣 | P0-P1 | 核实计费依据、特殊折扣、退款原因等，核对实际承运情况 |
| **货物损坏/破损** | 运单标记为货物损坏或包装破损，或客户投诉货物质量 | P0-P1 | 收集现场照片、确认损坏程度、评估赔偿、启动索赔流程 |
| **虚假签收** | 签收时间存在逻辑异常（如早于发货时间）或签收凭证可疑 | P0-P1 | 核实签收凭证真实性、通过客户确认、调查异常原因 |
| **时间异常** | 运单时间戳逻辑错误（如揽收时间早于发货时间）、未来时间等 | P0-P1 | 立即核查数据记录，与客户确认，修正时间数据 |
| **重量异常** | 申报重量异常（过大/过小）或超出产品类型标准 | P1-P2 | 确认是否数据录入错误、实际超重或产品分类错误 |

**示例待办项**:
```
标题: "运单WLYD5678298运费异常 - 高风险"
描述: "运费800元 vs 结算3617元，差异达452%（差额2817元）。货物：电子产品，客户：杨丽贸易公司。需核实计费依据和实际派送情况。"
优先级: P0
推荐执行人: 刘伟（财务核查员）
预期处理时间: 1小时内
```

### 6.2 任务问题

针对已下发任务的执行状态异常的待办项。

| 类型 | 判断标准 | 优先级 | 推荐处理 |
|-----|--------|------|--------|
| **任务超期** | 当前时间已超过截止时间，任务仍未完成 | P0-P1 | 立即跟进执行人，了解进展障碍，催促完成或调度支持 |
| **任务未更新** | 任务最后更新超过 48 小时（仍处于进行中） | P1-P2 | 确认执行人状态，是否遇到困难需要支持 |
| **进度缓慢** | 任务完成进度远低于预期（如截止 50% 但仅 20%） | P1-P2 | 评估是否需要调整资源、延期或重新分配 |
| **分配不当** | 任务分配给不适合的执行人 | P2 | 考虑重新分配给更合适的执行人 |

**示例待办项**:
```
标题: "任务TASK-001超期48小时 - 紧急"
描述: "任务\"运单WLYD9585102重量异常核查\" 截止时间已过2026-03-25 17:00，当前状态仍为\"进行中\"，进度40%。执行人：李经理(EMP_005)。最后更新时间：2026-03-24 16:30。"
优先级: P0
推荐执行人: 王经理（任务创建者，李经理直属领导）
预期处理时间: 立即
```

### 6.3 异常问题

针对业务执行和运营层面的异常问题的待办项，与运单数据问题和任务问题不重叠。

| 类型 | 判断标准 | 优先级 | 推荐处理 |
|-----|--------|------|--------|
| **执行人绩效下降** | 执行人的反馈率、准时率、处理质量等指标相比历史平均值下降 20% 以上，或投诉率上升 | P1-P2 | 了解执行人状态，是否遇到工作困难，是否需要支持或调整工作量 |
| **地区风险指标异常** | 某个地区的异常率/风险评分相比历史平均值上升 30% 以上，或出现新增高风险订单集中 | P1-P2 | 分析地区风险根源（如供应商变化、运输线路变化等），制定应对方案 |
| **客户/供应商异常** | 新出现的客户投诉率高于平均水平、供应商派件质量下降、或客户退货率异常增加 | P1-P2 | 联系客户/供应商了解原因，评估是否需要调整合作方式或重点关注 |
| **业务流程效率异常** | 某个运输环节的平均处理时间增加 50% 以上，或某类运单的处理周期明显延长 | P1-P3 | 分析流程瓶颈，优化操作流程，提升转运、配送等各环节效率 |

**示例待办项**:
```
标题: "刘伟执行人反馈率下降 - 需关注"
描述: "刘伟本周反馈率 65%，相比过去 4 周平均水平 (92%) 下降 27%。处理任务数未减，可能存在工作状态异常或工作量过大。"
优先级: P1
推荐执行人: 王经理（刘伟的直属领导）
预期处理时间: 2小时内
```

---

## 7. 交互流程

### 7.1 【一键下发】流程

```
Step 1: Manager 查看待办列表，点击 [查看详情→]
        ↓
Step 2: 右侧详情面板展开，显示：
        - 待办标题/描述
        - 原始数据表格
        - 推荐执行人（关键信息）
        - 预期处理时间
        ↓
Step 3: Manager 确认信息，点击 [一键下发] 按钮
        ↓
Step 4: 弹出预览确认对话框，显示：
        - 任务标题/描述
        - 下发对象：王经理
        - 截止时间：明天 17:00
        - [确认下发] [修改] [取消] 按钮
        ↓
Step 5a: 点击 [确认下发] → 后端创建 Task 记录
         待办项状态变更为 "已处理" → 卡片灰显
         左侧面板的 "任务追踪" Tab 新增任务卡片
         ↓
Step 5b: 点击 [修改] → 右侧详情允许编辑（执行人/截止时间）
         ↓
Step 5c: 点击 [取消] → 关闭对话框，不做任何改动
```

**关键点**:
- 预览必须显示，不允许直接下发
- 只能修改执行人和截止时间
- 确认下发后，待办项状态自动更新为 "已处理"

### 7.2 【修改推荐执行人】流程

```
Step 1: Manager 看到推荐执行人不满意
        ↓
Step 2: 点击待办卡片的 [添加到对话] 按钮
        ↓
Step 3: 待办项转为文本，添加到全局聊天区域
        （文本格式: "标题 + 推荐执行人 + 关键数据"）
        ↓
Step 4: Manager 在聊天输入框输入：
        "这个任务应该由李经理执行，他在数据分析方面更专业"
        ↓
Step 5: Agent 回复修改建议：
        "已更新推荐执行人为李经理，理由：..."
        ↓
Step 6: Manager 手动刷新页面 (Demo 阶段)
        左侧面板的待办项推荐执行人已变更
        ↓
Step 7: Manager 确认无误，点击 [一键下发]
```

**关键点**:
- 通过聊天与 Agent 交互进行推荐人修改
- Demo 阶段需要手动刷新查看更新
- Agent 不能自动修改前端展示，只能回复建议

### 7.3 【标记为已处理】流程

```
Step 1: Manager 手动处理完待办项
        ↓
Step 2: 点击待办卡片的 [标记为已处理] 按钮
        (或在详情面板中操作)
        ↓
Step 3: 后端更新待办项状态为 "已处理"
        ↓
Step 4: 前端更新卡片样式：
        - 背景色变灰
        - 文字变灰
        - opacity 降低到 0.6
        - 卡片被移到分组底部
        ↓
Step 5: 右侧详情面板自动清空
```

---

## 8. Mock 数据示例

### 8.1 完整的待办项 Mock 数据（20 个示例）

**说明**：以下20个示例基于实际运单和任务数据，涵盖：
- **运单数据问题** (12个): 时间异常、金额异常、货物损坏、虚假签收、重量异常、地址错误等
- **任务问题** (6个): 任务超期、任务未更新、进度缓慢、分配不当等
- **系统异常** (2个): API故障、数据质量问题等

```json
[
  {
    "id": "TODO-2026-001",
    "title": "运单WLYD9585102时间异常核查 - 高风险",
    "description": "运单时间逻辑混乱：揽收时间2026-12-24（未来时间）早于发货时间2025-09-09一年多，签收时间2025-02-11早于发货时间。货物：电子产品，重量1307kg，客户：王静贸易公司，地区：上海区。需紧急确认真实运单信息。",
    "category": "运单数据问题",
    "type": "时间异常",
    "priority": "P0",
    "status": "未处理",
    "severity": "critical",
    "source_data": {
      "date": "2026-03-25",
      "region": "华南",
      "metrics": {
        "import": 10000,
        "export": 15000,
        "span_percentage": 150
      }
    },
    "analysis": {
      "trend": "上升趋势明显，需关注",
      "change_rate": "150%",
      "affected_items": 5,
      "root_cause": "出口订单增加，进口原料减少"
    },
    "recommended_assignee": {
      "user_id": "user_002",
      "name": "王经理",
      "reason": "华南地区负责人，具有数据核查权限"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 24
    },
    "metadata": {
      "created_at": "2026-03-26T09:30:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T09:30:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-002",
    "title": "华东地区缺少 2026-03-25 数据",
    "description": "华东地区风险数据未按时上报，距预期时间已超 4 小时",
    "category": "风险数据问题",
    "type": "缺数据",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "date": "2026-03-25",
      "region": "华东",
      "expected_time": "2026-03-26T08:00:00Z",
      "actual_time": null
    },
    "analysis": {
      "trend": "延迟上报，可能系统故障或人员问题",
      "expected_items": 50,
      "received_items": 0,
      "root_cause": "待确认"
    },
    "recommended_assignee": {
      "user_id": "user_003",
      "name": "李数据",
      "reason": "数据管理员，负责数据导入"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 2
    },
    "metadata": {
      "created_at": "2026-03-26T12:15:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T12:15:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-003",
    "title": "华北地区评分异常预警",
    "description": "风险评分 87 分，较历史平均值高 35 分，建议重点关注",
    "category": "风险数据问题",
    "type": "评分异常",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "date": "2026-03-25",
      "region": "华北",
      "risk_score": 87,
      "historical_avg": 52,
      "threshold": 70
    },
    "analysis": {
      "trend": "风险评分大幅上升，需深入分析原因",
      "top_risk_factors": ["进出口异常", "库存堆积"],
      "recommendation": "建议立即启动风险应对方案"
    },
    "recommended_assignee": {
      "user_id": "user_001",
      "name": "张总经理",
      "reason": "总经理，负责全局风险评估"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 4
    },
    "metadata": {
      "created_at": "2026-03-26T10:45:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T10:45:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-004",
    "title": "TASK-2026-123 已超期 48 小时",
    "description": "任务\"华中风险数据分析\" 截止时间已过，当前状态仍为\"进行中\"",
    "category": "任务问题",
    "type": "任务超期",
    "priority": "P0",
    "status": "未处理",
    "severity": "critical",
    "source_data": {
      "task_id": "TASK-2026-123",
      "task_title": "华中风险数据分析",
      "deadline": "2026-03-24T17:00:00Z",
      "current_time": "2026-03-26T14:00:00Z",
      "overdue_hours": 45
    },
    "analysis": {
      "current_status": "进行中",
      "progress": 40,
      "assigned_to": "李经理",
      "last_update": "2026-03-24T16:30:00Z"
    },
    "recommended_assignee": {
      "user_id": "user_001",
      "name": "张总经理",
      "reason": "任务创建者，负责督促和协调"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 1
    },
    "metadata": {
      "created_at": "2026-03-26T14:05:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T14:05:00Z",
      "related_task_ids": ["TASK-2026-123"],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-005",
    "title": "TASK-2026-456 长期未更新（72 小时）",
    "description": "任务\"西南地区数据验证\" 已 72 小时未有任何更新，需了解进展",
    "category": "任务问题",
    "type": "长期未更新",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "task_id": "TASK-2026-456",
      "task_title": "西南地区数据验证",
      "created_at": "2026-03-23T09:00:00Z",
      "last_update": "2026-03-23T14:30:00Z",
      "hours_since_update": 72
    },
    "analysis": {
      "current_status": "进行中",
      "progress": 25,
      "assigned_to": "王经理",
      "possible_reasons": ["人员超负荷", "遇到技术困难", "优先级调整"]
    },
    "recommended_assignee": {
      "user_id": "user_002",
      "name": "王经理",
      "reason": "任务执行人，需主动汇报进展"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 2
    },
    "metadata": {
      "created_at": "2026-03-26T11:20:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T11:20:00Z",
      "related_task_ids": ["TASK-2026-456"],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-006",
    "title": "TASK-2026-789 进度缓慢预警",
    "description": "任务\"东南风险评估\"已 96 小时，进度仅 15%，预期进度应为 60%+",
    "category": "任务问题",
    "type": "进度缓慢",
    "priority": "P2",
    "status": "未处理",
    "severity": "medium",
    "source_data": {
      "task_id": "TASK-2026-789",
      "task_title": "东南风险评估",
      "created_at": "2026-03-22T08:00:00Z",
      "current_progress": 15,
      "expected_progress": 60,
      "assigned_to": "李经理"
    },
    "analysis": {
      "progress_gap": 45,
      "average_rate": "6% per day",
      "estimated_completion": "10 days",
      "deadline": "2026-03-31",
      "risk": "可能无法按时完成"
    },
    "recommended_assignee": {
      "user_id": "user_001",
      "name": "张总经理",
      "reason": "评估是否需要调整资源或截止时间"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-28",
      "priority_hours": 48
    },
    "metadata": {
      "created_at": "2026-03-26T09:50:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T09:50:00Z",
      "related_task_ids": ["TASK-2026-789"],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-007",
    "title": "风险数据导入系统故障",
    "description": "数据导入 API 返回 500 错误，影响华中、华东地区数据上传",
    "category": "异常问题",
    "type": "系统异常",
    "priority": "P0",
    "status": "未处理",
    "severity": "critical",
    "source_data": {
      "error_code": 500,
      "endpoint": "/api/risk-data/import",
      "affected_regions": ["华中", "华东"],
      "first_occurrence": "2026-03-26T13:45:00Z"
    },
    "analysis": {
      "service_status": "不可用",
      "error_message": "数据库连接超时",
      "impact": "无法导入新数据，影响数据完整性"
    },
    "recommended_assignee": {
      "user_id": "user_004",
      "name": "赵技术",
      "reason": "系统管理员，负责基础设施维护"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 1
    },
    "metadata": {
      "created_at": "2026-03-26T13:50:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T13:50:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-008",
    "title": "用户权限配置异常：李经理",
    "description": "李经理缺少\"数据导出\"权限，但需要为其所有报告添加此权限",
    "category": "异常问题",
    "type": "权限异常",
    "priority": "P2",
    "status": "未处理",
    "severity": "medium",
    "source_data": {
      "user_id": "user_003",
      "user_name": "李经理",
      "missing_permission": "data_export",
      "affected_operations": ["导出风险报告", "批量下载数据"],
      "request_time": "2026-03-26T14:20:00Z"
    },
    "analysis": {
      "current_role": "数据分析师",
      "required_role": "数据分析师 + 导出权限",
      "reason": "需要向客户提供定期报告"
    },
    "recommended_assignee": {
      "user_id": "user_005",
      "name": "管理员",
      "reason": "系统管理员，负责权限配置"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 24
    },
    "metadata": {
      "created_at": "2026-03-26T14:25:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T14:25:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-009",
    "title": "浙江地区风险评分异常",
    "description": "浙江地区风险评分突增至 92 分，涉及进出口和库存两个维度",
    "category": "风险数据问题",
    "type": "评分异常",
    "priority": "P0",
    "status": "未处理",
    "severity": "critical",
    "source_data": {
      "date": "2026-03-25",
      "region": "浙江",
      "risk_score": 92,
      "previous_score": 58,
      "change": 34
    },
    "analysis": {
      "contributing_factors": {
        "进出口风险": 95,
        "库存风险": 88,
        "市场风险": 65
      },
      "root_cause": "大订单取消，库存积压，进口延迟"
    },
    "recommended_assignee": {
      "user_id": "user_006",
      "name": "孙浙江负责人",
      "reason": "浙江地区负责人，最了解当地情况"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 24
    },
    "metadata": {
      "created_at": "2026-03-26T10:15:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T10:15:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-010",
    "title": "江苏地区进出口倍数异常",
    "description": "进出口比例达 1:8，远超历史平均 1:2，需核实数据真实性",
    "category": "风险数据问题",
    "type": "跨度异常",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "date": "2026-03-25",
      "region": "江苏",
      "import": 2000,
      "export": 16000,
      "ratio": "1:8",
      "historical_avg_ratio": "1:2"
    },
    "analysis": {
      "trend": "出口激增，可能受新订单驱动",
      "change_rate": "400%",
      "data_quality": "需确认是否重复计算"
    },
    "recommended_assignee": {
      "user_id": "user_007",
      "name": "吴江苏负责人",
      "reason": "江苏地区负责人，具有数据审核权限"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 24
    },
    "metadata": {
      "created_at": "2026-03-26T11:30:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T11:30:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-011",
    "title": "福建地区库存数据缺失",
    "description": "福建地区库存数据缺少 5 个关键指标（SKU 库存、成本、周转率），影响风险评估准确性",
    "category": "风险数据问题",
    "type": "缺数据",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "date": "2026-03-25",
      "region": "福建",
      "missing_metrics": ["库存金额", "库存数量", "周转率", "滞销率", "成本占比"],
      "expected_count": 10,
      "received_count": 5
    },
    "analysis": {
      "impact": "无法准确评估库存风险，评分降低",
      "last_received": "2026-03-24",
      "trend": "持续缺失，需紧急处理"
    },
    "recommended_assignee": {
      "user_id": "user_008",
      "name": "郭福建负责人",
      "reason": "福建地区负责人，负责数据完整性"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 6
    },
    "metadata": {
      "created_at": "2026-03-26T12:40:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T12:40:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-012",
    "title": "TASK-2026-999 已超期 24 小时",
    "description": "任务\"北京市场分析\" 已超期，状态为\"进行中\"，当前进度 60%",
    "category": "任务问题",
    "type": "任务超期",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "task_id": "TASK-2026-999",
      "task_title": "北京市场分析",
      "deadline": "2026-03-25T17:00:00Z",
      "current_time": "2026-03-26T14:00:00Z",
      "overdue_hours": 21,
      "progress": 60
    },
    "analysis": {
      "completion_estimate": "2-3 小时内可完成",
      "blocker": "等待市场数据反馈",
      "assigned_to": "王经理"
    },
    "recommended_assignee": {
      "user_id": "user_001",
      "name": "张总经理",
      "reason": "了解延迟原因，是否可接受"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 2
    },
    "metadata": {
      "created_at": "2026-03-26T14:10:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T14:10:00Z",
      "related_task_ids": ["TASK-2026-999"],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-013",
    "title": "广东地区风险评分预警",
    "description": "广东地区风险评分升至 85 分，环比上升 18 分，重点关注出口业务",
    "category": "风险数据问题",
    "type": "评分异常",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "date": "2026-03-25",
      "region": "广东",
      "risk_score": 85,
      "previous_score": 67,
      "change": 18
    },
    "analysis": {
      "main_driver": "出口订单取消率上升至 12%（历史 5%）",
      "impact_range": "珠三角制造企业",
      "recommendation": "主动联系大客户，了解需求变化"
    },
    "recommended_assignee": {
      "user_id": "user_009",
      "name": "陈广东负责人",
      "reason": "广东地区负责人，掌握客户关系"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 24
    },
    "metadata": {
      "created_at": "2026-03-26T09:00:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T09:00:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-014",
    "title": "山东地区缺少配套数据",
    "description": "山东地区风险评分为 78，但配套的详细数据（物流、融资等）未更新",
    "category": "风险数据问题",
    "type": "缺数据",
    "priority": "P2",
    "status": "未处理",
    "severity": "medium",
    "source_data": {
      "date": "2026-03-25",
      "region": "山东",
      "risk_score": 78,
      "missing_detail_categories": ["物流风险", "融资风险", "供应链风险"],
      "last_update": "2026-03-20"
    },
    "analysis": {
      "impact": "评分可能不准确，缺乏细节支撑",
      "estimated_delay": "3-5 天数据滞后"
    },
    "recommended_assignee": {
      "user_id": "user_010",
      "name": "赵山东负责人",
      "reason": "山东地区负责人"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-28",
      "priority_hours": 48
    },
    "metadata": {
      "created_at": "2026-03-26T13:20:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T13:20:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-015",
    "title": "上海地区评分异常预警",
    "description": "上海地区评分达 88 分，涉及多维度风险，需深入分析",
    "category": "风险数据问题",
    "type": "评分异常",
    "priority": "P0",
    "status": "未处理",
    "severity": "critical",
    "source_data": {
      "date": "2026-03-25",
      "region": "上海",
      "risk_score": 88,
      "previous_score": 62,
      "change": 26
    },
    "analysis": {
      "multi_dimension_risk": {
        "进出口": 90,
        "库存": 85,
        "融资": 92,
        "物流": 75
      },
      "critical_factors": ["融资成本上升", "库存压力大", "出口不确定性增加"]
    },
    "recommended_assignee": {
      "user_id": "user_001",
      "name": "张总经理",
      "reason": "总经理，需对集团战略做出反应"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 18
    },
    "metadata": {
      "created_at": "2026-03-26T08:30:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T08:30:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-016",
    "title": "TASK-2026-555 进度停滞 48 小时",
    "description": "任务\"四川风险评估\" 创建已 5 天，进度一直停留在 35%，最后更新在 2 天前",
    "category": "任务问题",
    "type": "长期未更新",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "task_id": "TASK-2026-555",
      "task_title": "四川风险评估",
      "created_at": "2026-03-21T09:00:00Z",
      "current_progress": 35,
      "last_update": "2026-03-24T10:30:00Z",
      "hours_without_update": 52
    },
    "analysis": {
      "assigned_to": "李经理",
      "deadline": "2026-03-28",
      "days_remaining": 2,
      "estimated_workload": "需要 5-6 天完成",
      "risk": "严重延期风险"
    },
    "recommended_assignee": {
      "user_id": "user_011",
      "name": "周四川负责人",
      "reason": "地区负责人，可提供现场支持"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-26",
      "priority_hours": 4
    },
    "metadata": {
      "created_at": "2026-03-26T10:50:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T10:50:00Z",
      "related_task_ids": ["TASK-2026-555"],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-017",
    "title": "王刚执行人反馈率下降 - 需关注",
    "description": "王刚本周反馈率 58%，相比过去 4 周平均水平 (88%) 下降 30%。处理任务数从平均 12 个/周降至 8 个/周，可能存在工作困难或工作量调整需求。",
    "category": "异常问题",
    "type": "执行人绩效下降",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "executor_id": "EMP_008",
      "executor_name": "王刚",
      "current_feedback_rate": 58,
      "historical_avg_rate": 88,
      "rate_drop": 30,
      "current_tasks_per_week": 8,
      "historical_avg_per_week": 12,
      "week": "2026-03-26"
    },
    "analysis": {
      "metric_change": "反馈率下降 30%，处理能力下降 33%",
      "possible_reasons": ["工作负荷过大", "个人状态异常", "工作流程调整"],
      "recommendation": "了解执行人状态，评估是否需要支持或调整工作量分配"
    },
    "recommended_assignee": {
      "user_id": "EMP_001",
      "name": "王经理",
      "reason": "王刚的直属领导，可进行绩效沟通"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 24
    },
    "metadata": {
      "created_at": "2026-03-26T13:15:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T13:15:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-018",
    "title": "TASK-2026-222 进度缓慢",
    "description": "任务\"海南消费者分析\" 执行已 3 天，进度仅 10%，预计完成需 20 天，严重延期风险",
    "category": "任务问题",
    "type": "进度缓慢",
    "priority": "P2",
    "status": "未处理",
    "severity": "medium",
    "source_data": {
      "task_id": "TASK-2026-222",
      "task_title": "海南消费者分析",
      "created_at": "2026-03-23T14:00:00Z",
      "current_progress": 10,
      "expected_progress_by_today": 40,
      "assigned_to": "高经理"
    },
    "analysis": {
      "completion_estimate_days": 20,
      "deadline": "2026-03-31",
      "days_remaining": 5,
      "likelihood": "几乎无法按时完成"
    },
    "recommended_assignee": {
      "user_id": "user_001",
      "name": "张总经理",
      "reason": "考虑是否需要延期或增加资源"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-27",
      "priority_hours": 24
    },
    "metadata": {
      "created_at": "2026-03-26T09:40:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T09:40:00Z",
      "related_task_ids": ["TASK-2026-222"],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-019",
    "title": "报表生成 API 超时",
    "description": "报表生成 API 响应时间超过 30 秒，多次请求超时，影响用户体验",
    "category": "异常问题",
    "type": "系统异常",
    "priority": "P2",
    "status": "未处理",
    "severity": "medium",
    "source_data": {
      "endpoint": "/api/reports/generate",
      "avg_response_time": 45000,
      "threshold": 5000,
      "timeout_count_today": 8,
      "started": "2026-03-26T08:00:00Z"
    },
    "analysis": {
      "root_cause": "可能是数据库查询优化不足或并发请求过多",
      "impact": "用户等待时间长，体验差",
      "suggestion": "需要数据库索引优化或缓存方案"
    },
    "recommended_assignee": {
      "user_id": "user_004",
      "name": "赵技术",
      "reason": "性能调优需要技术支持"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-28",
      "priority_hours": 48
    },
    "metadata": {
      "created_at": "2026-03-26T11:00:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T11:00:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  },
  {
    "id": "TODO-2026-020",
    "title": "华东地区异常率突增 - 高风险",
    "description": "华东地区本周异常率 12.5%，相比过去 4 周平均水平 (4.8%) 上升 7.7 个百分点 (增幅 160%)。高风险订单集中在运费异常和虚假签收两类，需分析根源并采取措施。",
    "category": "异常问题",
    "type": "地区风险指标异常",
    "priority": "P1",
    "status": "未处理",
    "severity": "high",
    "source_data": {
      "region": "华东",
      "week": "2026-03-26",
      "current_abnormal_rate": 12.5,
      "historical_avg_rate": 4.8,
      "rate_increase": 7.7,
      "increase_percentage": 160,
      "high_risk_count": 58,
      "abnormality_types": ["运费异常", "虚假签收", "货物损坏"],
      "affected_suppliers": ["供应商A", "供应商B"]
    },
    "analysis": {
      "trend": "异常率持续上升，已连续 3 周上升",
      "possible_causes": ["新增供应商质量问题", "运输线路变化", "人员调整影响"],
      "impact": "客户投诉率提高 45%，可能影响地区信誉评分"
    },
    "recommended_assignee": {
      "user_id": "EMP_009",
      "name": "陈华东负责人",
      "reason": "华东地区负责人，可进行实地调查和改进措施"
    },
    "expected_handling_time": {
      "start_date": "2026-03-26",
      "due_date": "2026-03-28",
      "priority_hours": 48
    },
    "metadata": {
      "created_at": "2026-03-26T10:20:00Z",
      "created_by": "system",
      "updated_at": "2026-03-26T10:20:00Z",
      "related_task_ids": [],
      "related_chat_messages": []
    }
  }
]
```

### 8.2 分类统计

从 20 个示例数据来看：

**按类别统计**:
- 运单数据问题: 12 个 (60%)
  - 时间异常: 3 个
  - 金额异常: 2 个
  - 货物损坏/破损: 3 个
  - 虚假签收: 3 个
  - 重量异常: 1 个
- 任务问题: 6 个 (30%)
  - 任务超期: 2 个
  - 任务未更新: 1 个
  - 进度缓慢: 1 个
  - 分配不当: 1 个
- 异常问题: 2 个 (10%)
  - 执行人绩效下降: 1 个
  - 地区风险指标异常: 1 个

**按优先级统计**:
- P0: 6 个 (30%)
- P1: 10 个 (50%)
- P2: 4 个 (20%)

---

## 9. 实现指南

### 9.1 Phase 1: UI 框架 + Mock 数据 (第 1-2 周)

#### 目标
- 完整的 3 列布局 (Left Tab + Main Content + Right Detail)
- 三个 Tab 页面的基础渲染
- 待办卡片和分组的样式
- Mock 数据集成

#### 需要创建的文件

**前端组件**:
```
frontend/src/components/
├── TodoPage/
│   ├── TodoPage.jsx              # 主容器组件
│   ├── TodoPage.css              # 样式文件
│   ├── TodoLeftSidebar.jsx        # 左侧 Tab 栏
│   ├── TodoLeftSidebar.css
│   ├── TodoMainContent.jsx        # 中间内容区
│   ├── TodoMainContent.css
│   ├── TodoCard.jsx               # 待办卡片组件
│   ├── TodoCard.css
│   ├── TodoGroup.jsx              # 分组容器
│   ├── TodoGroup.css
│   ├── DetailPanel.jsx            # 右侧详情面板
│   ├── DetailPanel.css
│   ├── TabToday.jsx               # Tab 1: 今日待办
│   ├── TabRiskData.jsx             # Tab 2: 风险数据
│   ├── TabTaskTracking.jsx        # Tab 3: 任务追踪
│   └── ChatArea.jsx               # 底部聊天区 (集成现有)
```

**Mock 数据**:
```
frontend/src/data/
├── mockTodos.js                  # 20 个待办项数据
├── mockTasks.js                  # 任务数据
├── mockRiskData.js               # 风险数据
└── mockUsers.js                  # 用户列表
```

#### Phase 1 代码示例

**架构说明**：
- 在现有的 App.jsx 3 栏布局基础上进行改造
- 左栏：原来的对话历史改为 3 个 Tab 页面
- 中栏：保持对话区域不变
- 右栏：新增详情面板（独立的展开/折叠控制，不受 Tab 影响）

**App.jsx 改动** (伪代码示意):
```jsx
// 原来：
<div className="App">
  <ChatHistory />  {/* 左栏 - 聊天历史 */}
  <ChatArea />     {/* 中栏 - 对话区 */}
  <empty />        {/* 右栏 - 空 */}
</div>

// 改为：
<div className="App">
  <TodoTabs />     {/* 左栏 - Tab 切换：今日待办/风险数据/任务追踪 */}
  <ChatArea />     {/* 中栏 - 对话区（保持不变）*/}
  <DetailPanel />  {/* 右栏 - 详情面板（独立展开/折叠，点击卡片自动弹出）*/}
</div>
```

**新增前端文件** (Phase 1):
```
frontend/src/components/
├── TodoTabs.jsx                # 左栏 Tab 容器
├── TodoTabs.css
├── TabToday.jsx                # Tab 1: 今日待办
├── TabToday.css
├── TabRiskData.jsx             # Tab 2: 风险数据（复用现有）
├── TabTaskTracking.jsx         # Tab 3: 任务追踪（复用现有）
├── TodoCard.jsx                # 待办项卡片
├── TodoCard.css
├── DetailPanel.jsx             # 右栏详情面板
└── DetailPanel.css
```

#### 右栏交互逻辑说明

**DetailPanel 组件的核心功能**:

1. **独立的展开/折叠状态管理**
   - 右栏有独立的 `isExpanded` 状态，不依赖于当前 Tab
   - 用户可通过右上角的关闭按钮手动折叠右栏
   - 切换 Tab 时，右栏的展开/折叠状态保持不变

2. **自动弹出逻辑**
   - 点击待办项卡片 → 触发 `onSelectTodo(todoItem)` 回调
   - 点击任务卡片 → 触发 `onSelectTask(taskItem)` 回调
   - 这两个回调自动设置 `isExpanded = true`，使右栏弹出

3. **内容更新逻辑**
   - DetailPanel 维护两个状态：`selectedTodo` 和 `selectedTask`
   - 根据当前 `selectedTodo` 或 `selectedTask` 显示对应内容
   - 从其他 Tab 切换回来时，如果有之前选中的项，继续显示该项的详情

4. **状态流转示例**
   ```
   初始状态: isExpanded=false, selectedTodo=null, selectedTask=null

   用户点击待办项卡片 →
     isExpanded=true, selectedTodo=todo_001, selectedTask=null

   用户切换到「风险数据」Tab →
     isExpanded=true（保持）, selectedTodo=todo_001（保持）, selectedTask=null

   用户点击任务卡片 →
     isExpanded=true, selectedTodo=null, selectedTask=task_001

   用户点击关闭按钮 →
     isExpanded=false, selectedTodo=null, selectedTask=null
   ```

5. **App.jsx 中的集成**
   ```jsx
   export default function App() {
     const [detailPanel, setDetailPanel] = useState({
       isExpanded: false,
       selectedTodo: null,
       selectedTask: null
     });

     const handleSelectTodo = (todo) => {
       setDetailPanel({
         isExpanded: true,
         selectedTodo: todo,
         selectedTask: null
       });
     };

     const handleSelectTask = (task) => {
       setDetailPanel({
         isExpanded: true,
         selectedTodo: null,
         selectedTask: task
       });
     };

     const handleCloseDetail = () => {
       setDetailPanel({
         isExpanded: false,
         selectedTodo: null,
         selectedTask: null
       });
     };

     return (
       <div className="App">
         <TodoTabs
           onSelectTodo={handleSelectTodo}
           onSelectTask={handleSelectTask}
         />
         <ChatArea />
         <DetailPanel
           isExpanded={detailPanel.isExpanded}
           selectedTodo={detailPanel.selectedTodo}
           selectedTask={detailPanel.selectedTask}
           onClose={handleCloseDetail}
         />
       </div>
     );
   }
   ```

#### 左栏折叠/展开逻辑说明

**TodoTabs 组件的展开/折叠控制**:

1. **独立的展开/折叠状态管理**
   - 左栏有独立的 `isCollapsed` 状态，不依赖于当前 Tab
   - 用户可通过左栏顶部的折叠按钮（< 符号）手动折叠左栏
   - 切换 Tab 时，左栏的展开/折叠状态保持不变

2. **样式自适应**
   - **展开时**：左栏显示为 ~300px 宽，显示 Tab 内容
   - **折叠时**：左栏宽度变为 ~40px，仅显示折叠按钮（变为 > 符号）
   - 中栏宽度自动扩展，占据展开的空间

3. **Tab 按钮在折叠状态下**
   - 保持可见和可点击（可显示为图标或隐藏）
   - 点击仍能切换 Tab（后台切换，内容不可见）
   - 用户可点击展开按钮后查看内容

4. **App.jsx 中的集成**
   ```jsx
   export default function App() {
     const [sidebarState, setSidebarState] = useState({
       isLeftCollapsed: false,
       activeTab: 'today'
     });

     const handleToggleLeftSidebar = () => {
       setSidebarState(prev => ({
         ...prev,
         isLeftCollapsed: !prev.isLeftCollapsed
       }));
     };

     const handleTabChange = (tabName) => {
       setSidebarState(prev => ({
         ...prev,
         activeTab: tabName
       }));
     };

     return (
       <div className="App" style={{
         display: 'grid',
         gridTemplateColumns: `${sidebarState.isLeftCollapsed ? '40px' : '300px'} 1fr ${detailPanel.isExpanded ? '350px' : '0px'}`,
         height: '100vh'
       }}>
         <TodoTabs
           isCollapsed={sidebarState.isLeftCollapsed}
           onToggleCollapse={handleToggleLeftSidebar}
           activeTab={sidebarState.activeTab}
           onTabChange={handleTabChange}
           onSelectTodo={handleSelectTodo}
           onSelectTask={handleSelectTask}
         />
         <ChatArea />
         <DetailPanel
           isExpanded={detailPanel.isExpanded}
           selectedTodo={detailPanel.selectedTodo}
           selectedTask={detailPanel.selectedTask}
           onClose={handleCloseDetail}
         />
       </div>
     );
   }
   ```

5. **TodoTabs 组件内部实现**
   ```jsx
   export default function TodoTabs({
     isCollapsed,
     onToggleCollapse,
     activeTab,
     onTabChange,
     onSelectTodo,
     onSelectTask
   }) {
     return (
       <div className={`todo-tabs ${isCollapsed ? 'collapsed' : ''}`}>
         {/* Tab 控制栏 */}
         <div className="tab-controls">
           <div className="tab-buttons">
             <button className={`tab-btn ${activeTab === 'today' ? 'active' : ''}`}
               onClick={() => onTabChange('today')} title="今日待办">
               📋
             </button>
             <button className={`tab-btn ${activeTab === 'riskData' ? 'active' : ''}`}
               onClick={() => onTabChange('riskData')} title="风险数据">
               📊
             </button>
             <button className={`tab-btn ${activeTab === 'tasks' ? 'active' : ''}`}
               onClick={() => onTabChange('tasks')} title="任务追踪">
               ✓
             </button>
           </div>

           {/* 折叠/展开按钮 */}
           <button className="toggle-btn" onClick={onToggleCollapse}
             title={isCollapsed ? '展开左栏' : '折叠左栏'}>
             {isCollapsed ? '>' : '<'}
           </button>
         </div>

         {/* Tab 内容（折叠时隐藏） */}
         {!isCollapsed && (
           <div className="tab-content">
             {activeTab === 'today' && <TabToday onSelectTodo={onSelectTodo} />}
             {activeTab === 'riskData' && <TabRiskData />}
             {activeTab === 'tasks' && <TabTaskTracking onSelectTask={onSelectTask} />}
           </div>
         )}
       </div>
     );
   }
   ```

**TodoCard.css** (卡片样式):
```css
.todo-card {
  cursor: pointer;
  border-left-width: 4px;
  transition: all 0.2s ease;
}

.todo-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.todo-card.selected {
  border-color: var(--primary-color);
  background: var(--primary-light);
}

.todo-card.processed {
  opacity: 0.6;
  background: var(--bg-gray);
}

.todo-header {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  align-items: center;
}

.priority-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}

.priority-badge.priority-p0 {
  background: var(--danger-color);
}

.priority-badge.priority-p1 {
  background: var(--warning-color);
}

.priority-badge.priority-p2 {
  background: var(--primary-color);
}

.priority-badge.priority-p3 {
  background: var(--text-disabled);
}

.todo-type {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 0 var(--spacing-xs);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.todo-timestamp {
  font-size: 11px;
  color: var(--text-disabled);
  margin-left: auto;
}

.todo-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: var(--spacing-sm) 0;
}

.todo-description {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: var(--spacing-md);
}

.todo-assignee {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: #f9f9f9;
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-md);
  font-size: 12px;
}

.todo-assignee .label {
  color: var(--text-secondary);
  font-weight: 500;
}

.todo-assignee .value {
  color: var(--primary-color);
  font-weight: 600;
}

.todo-footer {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.status-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.status-unprocessed {
  background: #fef3c7;
  color: #b45309;
}

.status-badge.status-processed {
  background: #dcfce7;
  color: #15803d;
}
```

### 9.2 Phase 2: 后端 API + 文件存储 (第 3-4 周)

#### 目标
- 实现 `/api/todos/*` 所有端点
- 实现文件存储机制 (JSON 文件)
- 与前端 Mock 数据切换

#### 需要创建的文件

**后端模块**:
```
backend/
├── agents/
│   └── todos/                    # 待办项模块
│       ├── __init__.py
│       ├── model.py              # TodoItem 数据模型
│       ├── service.py            # 业务逻辑
│       ├── storage.py            # 文件存储 (JSON)
│       └── api.py                # API 路由
└── data/
    └── todos/                    # 数据存储目录
        ├── todos.json            # 待办项数据
        ├── tasks.json            # 任务数据
        └── archive/              # 已处理的待办项归档
```

#### Phase 2 代码示例

**backend/agents/todos/model.py** (数据模型):
```python
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class RecommendedAssignee:
    user_id: str
    name: str
    reason: str

@dataclass
class TodoItem:
    id: str
    title: str
    description: str
    category: str  # 风险数据问题 | 任务问题 | 异常问题
    type: str
    priority: str  # P0 | P1 | P2 | P3
    status: str  # 未处理 | 已处理
    severity: str
    source_data: Dict[str, Any]
    analysis: Dict[str, Any]
    recommended_assignee: RecommendedAssignee
    expected_handling_time: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['recommended_assignee'] = asdict(self.recommended_assignee)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        assignee_data = data.pop('recommended_assignee')
        assignee = RecommendedAssignee(**assignee_data)
        return cls(recommended_assignee=assignee, **data)
```

**backend/agents/todos/storage.py** (文件存储):
```python
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from .model import TodoItem

class TodoStorage:
    def __init__(self, data_dir: str = "data/todos"):
        self.data_dir = Path(data_dir)
        self.todos_file = self.data_dir / "todos.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_todos(self) -> List[TodoItem]:
        """加载所有待办项"""
        if not self.todos_file.exists():
            return []

        with open(self.todos_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return [TodoItem.from_dict(item) for item in data]

    def save_todos(self, todos: List[TodoItem]) -> None:
        """保存待办项列表"""
        data = [todo.to_dict() for todo in todos]
        with open(self.todos_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_todo(self, todo_id: str) -> Optional[TodoItem]:
        """获取单个待办项"""
        todos = self.load_todos()
        for todo in todos:
            if todo.id == todo_id:
                return todo
        return None

    def update_todo(self, todo_id: str, **kwargs) -> Optional[TodoItem]:
        """更新待办项"""
        todos = self.load_todos()
        for i, todo in enumerate(todos):
            if todo.id == todo_id:
                # 更新指定字段
                for key, value in kwargs.items():
                    if hasattr(todo, key):
                        setattr(todo, key, value)
                todos[i] = todo
                self.save_todos(todos)
                return todo
        return None
```

**backend/agents/todos/api.py** (API 路由):
```python
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from .service import TodoService

router = APIRouter(prefix="/api/todos", tags=["todos"])
service = TodoService()

@router.get("/today")
async def get_today_todos(
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
):
    """获取今日待办项"""
    return await service.get_today_todos(priority, category, region)

@router.get("/{todo_id}")
async def get_todo(todo_id: str):
    """获取单个待办项"""
    todo = await service.get_todo(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"success": True, "data": todo}

@router.post("/{todo_id}/execute")
async def execute_todo(
    todo_id: str,
    confirmation: bool = True,
    assigned_to_user_id: str = None,
    deadline_offset_hours: int = 24,
):
    """执行待办项（一键下发）"""
    result = await service.execute_todo(
        todo_id,
        confirmation,
        assigned_to_user_id,
        deadline_offset_hours
    )
    return {"success": True, "data": result}

@router.patch("/{todo_id}")
async def update_todo(todo_id: str, updates: dict):
    """更新待办项"""
    todo = await service.update_todo(todo_id, **updates)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"success": True, "data": todo}
```

### 9.3 Phase 3: 优化与完善 (第 5-6 周)

#### 目标
- 实现 Agent 自动扫描生成待办项
- 实现待办项修改建议（通过对话）
- 性能优化和前端交互完善
- 完整的单元测试

#### 工作项
1. Manager Agent 增强
   - 自动扫描风险数据异常
   - 自动扫描任务问题
   - 自动扫描系统异常

2. Skill 开发
   - `todo_generator` - 生成待办项
   - `todo_modifier` - 修改推荐人等
   - `todo_executor` - 执行下发

3. 前端完善
   - WebSocket 实时更新
   - 拖拽排序
   - 高级筛选和搜索
   - 批量操作

4. 测试覆盖
   - 单元测试 (Pytest)
   - 集成测试
   - E2E 测试 (Playwright)

---

## 10. 文件清单

### 10.1 前端文件清单（Phase 1）

```
frontend/src/components/
├── App.jsx                       # 主入口（改造：添加 DetailPanel 到右栏）
├── App.css                       # 全局样式（保持不变）
│
├── ChatArea.jsx                  # 中栏对话区（保持现有，无改动）
├── ChatArea.css                  # 保持现有
│
├── TodoTabs.jsx                  # 左栏 Tab 容器（新增）
├── TodoTabs.css                  # Tab 样式（新增）
│
├── TabToday.jsx                  # Tab 1: 今日待办（新增）
├── TabToday.css                  # 今日待办样式（新增）
├── TodoCard.jsx                  # 待办项卡片组件（新增）
├── TodoCard.css                  # 待办卡片样式（新增）
│
├── TabRiskData.jsx               # Tab 2: 风险数据（复用现有左栏上半部分）
├── TabRiskData.css               # 使用现有样式
│
├── TabTaskTracking.jsx           # Tab 3: 任务追踪（复用现有左栏下半部分）
├── TabTaskTracking.css           # 使用现有样式
│
├── DetailPanel.jsx               # 右栏详情面板（新增）
└── DetailPanel.css               # 详情面板样式（新增）

frontend/src/data/
├── mockTodos.js                  # 20 个待办项数据（新增）
├── mockUsers.js                  # 用户列表（可选）
└── index.js                      # 导出 Mock 数据
```

**说明**:
- TabRiskData 和 TabTaskTracking 直接包装现有的 RiskDataTable 和 TaskList 组件
- TodoTabs 管理 Tab 状态，根据 activeTab 显示不同内容
- DetailPanel 根据当前 Tab 和选中项显示不同内容

### 10.2 后端文件清单

```
backend/
├── agents/
│   └── todos/                         # 待办项模块（Phase 2 新增）
│       ├── __init__.py
│       ├── model.py                   # TodoItem 数据模型
│       ├── service.py                 # 业务逻辑服务
│       ├── storage.py                 # 文件存储接口（JSON）
│       ├── api.py                     # FastAPI 路由
│       └── tests/
│           ├── test_model.py
│           ├── test_service.py
│           └── test_api.py
│
└── data/
    └── todos/                         # 待办项数据存储（Phase 2）
        ├── todos.json                 # 待办项数据文件
        └── archive/                   # 已处理待办项归档
```

**说明**:
- Phase 1（Demo）：待办数据使用前端 mockTodos.js，无需后端存储
- Phase 2：实现后端 API，使用 JSON 文件存储待办项数据
- tasks.json 已在现有项目中使用，待办项下发时会创建新任务记录在 tasks.json

### 10.3 文档文件清单

```
docs/
├── TODOIST_FEATURE_DESIGN.md        # 本文件
├── IMPLEMENTATION_CHECKLIST.md       # 实现检查清单
├── API_REFERENCE.md                  # API 参考文档
├── MOCK_DATA_GENERATOR.md           # Mock 数据生成指南
└── TROUBLESHOOTING.md               # 故障排查指南
```

---

## 附录 A: 常见问题解答

**Q: 右侧详情面板如何在三个 Tab 间持续显示?**

A: 使用全局状态管理（如 Context 或 Redux），将 `selectedTodo` 保存在 TodoPage 组件的顶层状态，而不是 Tab 组件内部状态。这样切换 Tab 时，详情面板的状态不会丢失。

**Q: 一键下发后，待办项如何自动从待办列表移出?**

A: 待办项不会移出，只是状态变更为"已处理"，卡片灰显并被移到分组底部。这样 Manager 可以查看历史，同时新的未处理项排在前面。

**Q: Mock 数据如何切换为真实 API 数据?**

A: Phase 2 中，更改 `useTodos` Hook 的实现，从 `mockTodos` 切换到 API 调用（`fetch('/api/todos/today')`）。前端代码不需要大改，只需改数据源。

**Q: 如何实现 Agent 自动生成待办项?**

A: Phase 3 中，在 Manager Agent 的系统提示词中添加"自动扫描"规则，让 Agent 定期调用 `todo_generator` Skill，生成新的待办项。

---

## 附录 B: 设计原则

1. **用户至上**: 所有设计以 Manager 的操作效率为中心
2. **一致性**: 样式、交互、数据格式保持与现有项目一致
3. **渐进性**: 从 Mock 逐步演进到真实数据和 Agent 自动化
4. **可追溯性**: 所有待办项保留创建和更新记录，便于审计
5. **灵活性**: 支持用户自定义规则，规则引擎可扩展

---

**文档完成日期**: 2026-03-26
**维护负责人**: 待确定
**最后更新**: 2026-03-26

