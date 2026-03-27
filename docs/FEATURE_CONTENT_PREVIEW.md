# DJAgent 对话内容预览功能完整改造方案

## 📋 目录

1. [项目概述](#项目概述)
2. [设计目标](#设计目标)
3. [当前系统分析](#当前系统分析)
4. [新的消息格式定义](#新的消息格式定义)
5. [右侧面板架构设计](#右侧面板架构设计)
6. [向后兼容迁移方案](#向后兼容迁移方案)
7. [实施路线图](#实施路线图)
8. [技术栈选型](#技术栈选型)
9. [常见问题](#常见问题)

---

## 项目概述

### 背景

DJAgent是一个AI驱动的风险管理系统，采用**React + FastAPI + Claude Agent SDK**架构，包含Manager（业务负责人）和Staff（一线操作人员）两个端点。

当前系统支持文本和表单卡片两种消息类型，但随着Agent能力的增强，需要支持更多内容类型（表格、代码、图表、文档、图片等），并提供统一的内容预览能力。

### 核心需求

1. **WEB端（Manager）对话界面优化**
   - 右侧面板从单纯的任务详情扩展为通用内容预览面板
   - 支持表格、代码、图表、文档、图片、日志等多种内容类型
   - 点击消息中的内容可在右侧面板预览和编辑

2. **UI/UX设计**
   - 三栏式布局保持（已有可拖拽宽度调整和右侧折叠）
   - 右侧面板根据内容类型动态渲染，无需Tab页切换
   - 操作按钮采用icon-only设计（小图标），简约高效
   - 按钮根据content metadata动态生成

3. **兼容性要求**
   - 不破坏当前的表单渲染功能（Staff端）
   - Manager端和Staff端对话都需支持
   - 向后兼容旧消息格式

### 参考产品

| 产品 | 核心特性 | 参考价值 |
|------|--------|--------|
| Claude Artifacts | 右侧独立预览，Code/Preview标签，实时渲染 | UI布局、内容分离 |
| Genspark | 多类型内容预览，Sparkpage动态结果页 | 内容类型支持 |
| Coze | Preview & Debug面板，实时测试日志 | 调试面板设计 |
| LibreChat | 开源ChatGPT克隆，Artifacts支持 | 工程参考 |

---

## 设计目标

### 功能目标

- ✅ 支持 6+ 种内容类型（表格、代码、图表、文档、图片、日志）
- ✅ 统一的内容预览面板（无Tab页，自动选择渲染器）
- ✅ 动态操作按钮系统（根据metadata自动生成icon按钮）
- ✅ 部分内容可编辑反馈（表格、代码可编辑，修改后发送反馈给Agent）
- ✅ 完整的导出/下载功能（表格导出为CSV/XLSX，代码下载，图表导出PNG等）

### 非功能目标

- **兼容性**: 100% 向后兼容旧消息格式，无缝迁移
- **性能**: 预览加载 < 200ms，虚拟滚动支持大表格
- **可维护性**: 通用渲染引擎，新增类型无需修改核心逻辑
- **可扩展性**: 新增content type完全透明，无需改动Agent定义
- **用户体验**: 响应式设计，平板和移动端也能使用

### 成功指标

- 80% 的Agent回复包含多种内容混合
- 用户在右侧面板停留时间增加 30%（内容预览有价值）
- 无新的客户端错误日志（兼容性验证）
- 表单提交成功率保持 99%+（功能完整性）

---

## 当前系统分析

### 3.1 架构现状

#### 消息流向

```
Backend (unified_agent.py + app_fastapi.py)
    ↓
Agent生成回复 + 提取form_card JSON
    ↓
构建消息结构 (type/message_type + schema)
    ↓ HTTP Response
Frontend
    ├─ Manager端: ChatMessage 检查 msg.type
    └─ Staff端: App.jsx 检查 msg.type === 'form_card'
```

#### 当前消息格式

```javascript
// 纯文本消息
{
  timestamp: "2026-03-26T14:30:00Z",
  sender: "agent",
  message: "这是Agent回复",
  type: "text",
  message_type: "text"
}

// 表单卡片消息
{
  timestamp: "2026-03-26T14:30:05Z",
  sender: "agent",
  message: "请填写以下表单", // 文本说明
  type: "form_card",
  message_type: "form_card",
  schema: { form_id, title, sections, ... },
  form_id: "form_check_000-..."
}

// 总结卡片消息
{
  timestamp: "2026-03-26T14:30:10Z",
  sender: "agent",
  type: "summary_card",
  message_type: "summary_card",
  title: "任务总结",
  status: "completed",
  data: { ... }
}
```

### 3.2 关键依赖关系

#### Backend (app_fastapi.py, 第1100-1200行)

```python
# 消息构建
agent_reply = {
    "timestamp": timestamp,
    "sender": "Agent",
    "message": ai_response,
    "message_type": "text",  # ← 枚举值
}

# 提取form_card JSON
if match:  # markdown code block 中的JSON
    agent_reply["message_type"] = "form_card"
    agent_reply["type"] = "form_card"
    agent_reply["schema"] = schema
    agent_reply["form_id"] = form_id
```

**问题**: 消息格式写死了枚举，新增类型需改代码

#### Manager端 (ChatMessage.jsx, 第40-117行)

```javascript
const { type = 'text', schema, form_id, ... } = message

if (type === 'text') { /* 渲染markdown */ }
if (type === 'form_card') { /* 显示FormCardBubble */ }
if (type === 'summary_card') { /* 显示总结卡片 */ }
```

**问题**: 依赖顶级 type 字段，新增类型需改此文件

#### Staff端 (App.jsx, 第1843行)

```javascript
{msg.type === 'form_card' && msg.schema ? (
  <FormCardBubble
    schema={{
      ...msg.schema,
      state: editingForms[msg.form_id] ? 'editable' : 'readonly',
      actions: { showSubmit, showCancel, showModify, ... }
    }}
    onSubmit={(formData) => handleFormSubmit(msg.form_id, msg.schema, formData)}
    onCancel={() => setEditingForms(...)}
    onModify={() => setEditingForms(...)}
  />
) : null}
```

**问题**: 依赖 msg.form_id 作为state key，新格式中改为 block.id

#### 表单提交流程 (App.jsx, 第1668-1750行)

```javascript
handleFormSubmit(formId, schema, formData) {
  // POST /api/tasks/{task_id}/submit_form
  // 更新 submittedForms[formId] 和 editingForms[formId]
}
```

**问题**: formId来源变化，需更新调用方

### 3.3 影响范围矩阵

| 组件 | 当前依赖 | 新格式后 | 影响程度 | 工作量 |
|------|--------|---------|--------|-------|
| **ChatMessage.jsx** | `msg.type` | `msg.blocks[].type` | 🔴 高 | 中 |
| **FormCardBubble.jsx** | `msg.schema` | `block.data` | 🟡 中 | 小 |
| **App.jsx (Manager)** | `msg.type` | `msg.blocks[].type` | 🔴 高 | 大 |
| **App.jsx (Staff)** | `msg.type === 'form_card'` | `msg.blocks[].type === 'form_card'` | 🔴 高 | 大 |
| **表单状态管理** | `submittedForms[form_id]` | `submittedForms[block.id]` | 🟡 中 | 中 |
| **Backend API** | `message_type` 枚举 | `blocks[]` 数组 | 🔴 高 | 大 |
| **消息持久化** | 旧格式存储 | 新格式存储 | 🟡 中 | 中 |

---

## 新的消息格式定义

### 4.1 通用内容块结构

```typescript
/**
 * 通用内容块 - 支持任意内容类型
 *
 * 核心优势：
 * - type是开放字符串，无需枚举
 * - data是通用容器，可包含任意结构
 * - metadata指导前端如何渲染
 * - mimeType提供标准化标识
 */
interface ContentBlock {
  // 必需字段
  id: string                          // 唯一标识（用于状态管理）
  type: string                        // 内容类型（无枚举限制）

  // 可选标识
  mimeType?: string                   // MIME type（参考LangChain方案）

  // 显示信息
  title?: string                      // 内容标题
  description?: string                // 内容描述

  // 核心数据容器（所有实际数据都在这里）
  data: Record<string, any>           // 通用数据容器

  // 渲染指引（告诉前端如何显示和交互）
  metadata?: {
    displayType?: 'table' | 'code' | 'chart' | 'image' | 'document' | 'video' | 'debug' | 'auto'
    height?: number                   // 建议高度(px)
    width?: number                    // 建议宽度(px)

    // 能力指引
    previewable?: boolean             // 是否可预览
    editable?: boolean                // 是否可编辑
    executable?: boolean              // 是否可执行（代码）
    downloadable?: boolean            // 是否可下载

    // 操作列表（动态生成icon按钮）
    actions?: Array<'copy' | 'edit' | 'download' | 'export' | 'execute' | 'fullscreen' | 'sort' | 'filter' | 'refresh' | 'share'>
  }
}

/**
 * 新的统一消息格式
 */
interface Message {
  // 基础字段（保持兼容）
  timestamp: string                   // ISO timestamp
  sender: 'user' | 'agent' | 'system'

  // 核心内容
  content?: string                    // 纯文本主内容（新标准字段）
  message?: string                    // 旧字段（向后兼容）

  // 扩展内容块（核心创新）
  blocks?: ContentBlock[]             // 内容块数组（新）

  // 元数据（保持兼容）
  metadata?: {
    agentThinking?: string            // Agent思考过程
    tokensUsed?: number               // Token消耗
    executionTime?: number            // 执行耐时(ms)
    relatedTasks?: string[]           // 关联任务ID
  }

  // 向后兼容字段（逐步废弃）
  type?: string                       // 旧：消息类型（已废弃，用block type替代）
  message_type?: string               // 旧：消息类型别称
  schema?: any                        // 旧：表单schema（已废弃，改为block.data）
  form_id?: string                    // 旧：表单ID（已废弃，改为block.id）
}
```

### 4.2 具体内容类型示例

#### 表格内容

```typescript
{
  id: "table_001",
  type: "table",
  mimeType: "application/x-table+json",
  title: "数据汇总表",
  description: "按地区统计的风险等级分布",
  data: {
    headers: ["地区", "高风险", "中风险", "低风险", "合计"],
    rows: [
      ["北京", 12, 45, 89, 146],
      ["上海", 8, 32, 56, 96],
      ["广州", 15, 28, 73, 116]
    ],
    summary?: "共3个地区，146条数据"
  },
  metadata: {
    displayType: "table",
    editable: true,                 // 支持编辑单元格
    actions: ["sort", "filter", "export", "edit", "download"]
  }
}
```

#### 代码内容

```typescript
{
  id: "code_001",
  type: "code",
  mimeType: "text/x-python",        // MIME type明确语言
  title: "风险分析代码",
  data: {
    code: "import pandas as pd\ndf = pd.read_csv('risk_data.csv')\n...",
    language: "python",
    filename: "risk_analysis.py",
    description: "用于分析风险数据的Python脚本"
  },
  metadata: {
    displayType: "code",
    editable: true,
    executable: true,               // 支持执行
    actions: ["copy", "execute", "edit", "download"]
  }
}
```

#### 图表内容

```typescript
{
  id: "chart_001",
  type: "chart",
  mimeType: "application/vnd.vegalite+json",  // Vega-Lite标准
  title: "风险等级分布趋势",
  data: {
    chartType: "bar",
    chartConfig: {
      // ECharts 或 Recharts 配置
      legend: { data: ["高", "中", "低"] },
      xAxis: { type: "category", data: ["北京", "上海", "广州"] },
      yAxis: { type: "value" },
      series: [...]
    }
  },
  metadata: {
    displayType: "chart",
    height: 400,
    actions: ["fullscreen", "download"]
  }
}
```

#### 图片内容

```typescript
{
  id: "image_001",
  type: "image",
  mimeType: "image/jpeg",
  title: "现场拍照",
  data: {
    url: "https://...",
    alt: "运单现场拍照",
    width: 800,
    height: 600
  },
  metadata: {
    displayType: "image",
    actions: ["fullscreen", "download"]
  }
}
```

#### 文档内容

```typescript
{
  id: "doc_001",
  type: "document",
  mimeType: "application/pdf",
  title: "合同扫描件",
  data: {
    fileType: "pdf",
    fileName: "contract.pdf",
    fileUrl: "https://...",
    pages: 5,
    size: 2048000  // 字节
  },
  metadata: {
    displayType: "document",
    actions: ["download", "fullscreen"]
  }
}
```

#### 调试日志内容

```typescript
{
  id: "debug_001",
  type: "debug",
  mimeType: "application/x-log+json",
  title: "执行日志",
  data: {
    logs: [
      {
        timestamp: "2026-03-26T14:30:00Z",
        level: "info",
        message: "开始处理文件",
        data: { filename: "data.csv" }
      },
      {
        timestamp: "2026-03-26T14:30:01Z",
        level: "warn",
        message: "发现异常数据",
        data: { row: 5, column: "price" }
      },
      {
        timestamp: "2026-03-26T14:30:02Z",
        level: "error",
        message: "处理失败",
        data: { error: "Invalid format" }
      }
    ],
    metrics: {
      duration: 2000,      // 毫秒
      memory: 51200000,    // 字节
      cpu: 45.2            // 百分比
    }
  },
  metadata: {
    displayType: "debug",
    actions: ["filter", "export", "copy"]
  }
}
```

#### 混合消息示例

```typescript
// Agent回复包含多个不同类型的内容
{
  timestamp: "2026-03-26T14:30:00Z",
  sender: "agent",
  content: "我分析了您的数据，发现以下规律：",  // 纯文本主内容
  blocks: [
    { id: "table_001", type: "table", data: {...} },
    { id: "chart_001", type: "chart", data: {...} },
    { id: "code_001", type: "code", data: {...} }
  ]
}
```

---

## 右侧面板架构设计

### 5.1 UI布局

```
┌────────────────────────────────────────────┐
│  预览头部：                                 │
│  ← [标题] | 操作按钮 (icon-only)          │
│  (📋 💾 📤 ⬇ ⚙ 等，根据metadata动态生成) │
├────────────────────────────────────────────┤
│                                            │
│        预览内容区（自动选择渲染器）        │
│                                            │
│  根据 block.metadata.displayType:          │
│  - 'table' → TablePreview                  │
│  - 'code' → CodePreview                    │
│  - 'chart' → ChartPreview                  │
│  - 'image' → ImagePreview                  │
│  - 'document' → DocumentPreview            │
│  - 'video' → VideoPreview                  │
│  - 'debug' → DebugPreview                  │
│                                            │
└────────────────────────────────────────────┘
```

### 5.2 组件架构

```
RightPanel/
├── index.jsx                          # 主面板组件
├── PreviewHeader.jsx                  # 头部（标题+动态按钮）
├── PreviewContent.jsx                 # 内容容器
├── PreviewRenderer.jsx                # 通用渲染器
├── previews/
│   ├── TablePreview.jsx               # 表格预览
│   ├── CodePreview.jsx                # 代码预览
│   ├── ChartPreview.jsx               # 图表预览
│   ├── ImagePreview.jsx               # 图片预览
│   ├── DocumentPreview.jsx            # 文档预览
│   ├── VideoPreview.jsx               # 视频预览
│   └── DebugPreview.jsx               # 调试日志预览
└── RightPanel.css                     # 样式文件
```

### 5.3 动态按钮实现

```javascript
// 操作按钮映射
const ICON_MAP = {
  copy: <Copy size={18} />,            // lucide-react图标
  edit: <Edit2 size={18} />,
  download: <Download size={18} />,
  export: <FileDown size={18} />,
  execute: <Play size={18} />,
  fullscreen: <Maximize2 size={18} />,
  sort: <ArrowUpDown size={18} />,
  filter: <Filter size={18} />,
  delete: <Trash2 size={18} />,
  refresh: <RotateCw size={18} />,
  share: <Share2 size={18} />,
}

// 操作处理器
const ACTION_HANDLERS = {
  copy: () => copyToClipboard(content),
  edit: () => openEditMode(),
  download: () => downloadContent(),
  export: () => showExportOptions(),
  execute: () => runCode(),
  fullscreen: () => toggleFullscreen(),
  sort: () => openSortDialog(),
  filter: () => openFilterPanel(),
  // ...
}

// 动态生成按钮
function RightPanel({ activeBlock }) {
  if (!activeBlock) return null

  const { metadata } = activeBlock
  const actions = metadata?.actions || []

  return (
    <div className="right-panel">
      <div className="preview-header">
        <span className="header-title">{activeBlock.title}</span>
        <div className="action-buttons">
          {actions.map(action => (
            <button
              key={action}
              className="icon-btn"
              title={action}
              onClick={() => ACTION_HANDLERS[action]?.()}
            >
              {ICON_MAP[action]}
            </button>
          ))}
        </div>
      </div>

      <PreviewRenderer block={activeBlock} />
    </div>
  )
}
```

---

## 向后兼容迁移方案

### 6.1 分层兼容策略

#### 第1层：API层（Backend）- 双格式输出

**原则**: Backend同时输出新格式和旧格式，前端优先使用新格式，降级使用旧格式。

```python
# app_fastapi.py 返回格式

{
    "status": "success",
    "agent_reply": {
        # 新格式（优先使用）
        "blocks": [
            {
                "id": "form_001",
                "type": "form_card",
                "mimeType": "application/x-form+json",
                "data": { "sections": [...] },
                "metadata": { "actions": [...] }
            }
        ],

        # 旧格式（向后兼容）
        "timestamp": "...",
        "sender": "Agent",
        "message": "文本内容",
        "message_type": "form_card",        # ← 保留
        "type": "form_card",                # ← 保留
        "schema": {...},                    # ← 保留
        "form_id": "form_001"               # ← 保留
    }
}
```

#### 第2层：Frontend规范化层（前端）

**原则**: 创建normalize函数，统一处理新旧格式，使业务逻辑只关心新格式。

```typescript
// frontend/src/utils/messageNormalizer.ts

/**
 * 将消息规范化为新格式
 * 如果已是新格式，直接返回
 * 如果是旧格式，自动转换为新格式
 */
export function normalizeMessage(msg: any): Message {
  // 如果已经是新格式，直接返回
  if (msg.blocks && msg.blocks.length > 0) {
    return msg
  }

  // 如果是旧格式，转换为新格式
  if (msg.type && msg.type !== 'text') {
    const block: ContentBlock = {
      id: msg.form_id || `${msg.type}_${Date.now()}`,
      type: msg.type,
      mimeType: msg.type === 'form_card' ? 'application/x-form+json' : undefined,
      data: msg.type === 'form_card' ? msg.schema : msg.data || {},
      metadata: {
        actions: msg.actions || []
      }
    }

    return {
      timestamp: msg.timestamp,
      sender: msg.sender,
      content: msg.message || msg.content,
      blocks: [block],
      // 保留旧字段以支持其他可能的兼容代码
      type: msg.type,
      message: msg.message,
      schema: msg.schema,
      form_id: msg.form_id
    }
  }

  // 纯文本消息转换
  return {
    timestamp: msg.timestamp,
    sender: msg.sender,
    content: msg.message || msg.content,
    message: msg.message,
    blocks: []
  }
}

/**
 * 反向转换：从新格式转回旧格式（用于API调用）
 */
export function denormalizeMessage(msg: Message): any {
  // 提取第一个非文本block的数据作为旧格式的顶级字段
  const firstBlock = msg.blocks?.[0]

  return {
    timestamp: msg.timestamp,
    sender: msg.sender,
    message: msg.content || msg.message,
    content: msg.content,
    blocks: msg.blocks,

    // 提取block信息到顶级（向后兼容）
    type: firstBlock?.type,
    message_type: firstBlock?.type,
    form_id: firstBlock?.id,
    schema: firstBlock?.data,
    metadata: firstBlock?.metadata
  }
}
```

#### 第3层：渲染层兼容

**原则**: ChatMessage等渲染组件只处理规范化后的消息，无需关心新旧格式。

```javascript
// frontend/src/components/ChatMessage.jsx

function ChatMessage({ message, onBlockClick }) {
  // 第1步：规范化消息
  const normalized = normalizeMessage(message)
  const { content, blocks, sender } = normalized

  return (
    <div className="chat-message">
      {/* 文本内容 */}
      {content && (
        <ReactMarkdown>{content}</ReactMarkdown>
      )}

      {/* 内容块指示 - 新方式 */}
      {blocks && blocks.length > 0 && (
        <div className="blocks-indicator">
          {blocks.map(block => (
            <button
              key={block.id}
              className="block-indicator-btn"
              onClick={() => onBlockClick(block)}
              title={block.title}
            >
              {getBlockIcon(block.type)}
              <span className="block-label">{block.title}</span>
            </button>
          ))}
        </div>
      )}

      {/* 向后兼容：显示旧格式的form_card */}
      {!blocks && message.type === 'form_card' && message.schema && (
        <FormCardBubble schema={message.schema} />
      )}
    </div>
  )
}
```

### 6.2 实施步骤

#### Step 1: 添加规范化层（无风险）

1. 创建 `frontend/src/utils/messageNormalizer.ts`
2. 创建 `frontend/src/types/message.ts`
3. 编写单元测试验证规范化逻辑

**时间**: 4h | **风险**: 低 | **文件数**: 2

#### Step 2: Backend双格式输出（低风险）

1. 修改 `app_fastapi.py` API响应，同时输出新旧格式
2. 修改 `unified_agent.py` JSON提取逻辑
3. 单元测试验证响应格式

**时间**: 6h | **风险**: 低 | **文件数**: 2

#### Step 3: Manager端适配（中等风险）

1. 更新 ChatMessage.jsx 使用 normalizeMessage
2. 保留向后兼容逻辑
3. 集成测试验证对话渲染

**时间**: 8h | **风险**: 中 | **文件数**: 1

#### Step 4: Staff端适配（中等风险）

1. 更新 App.jsx 表单处理逻辑
2. 更新state管理（submittedForms, editingForms使用block.id）
3. 集成测试验证表单流程

**时间**: 12h | **风险**: 中 | **文件数**: 1

#### Step 5: 右侧面板实现（低风险）

1. 创建 RightPanel 组件架构
2. 实现 PreviewRenderer 通用渲染器
3. 实现各专用预览器（Table, Code, Chart等）
4. 集成到Manager端

**时间**: 40h | **风险**: 低 | **文件数**: 8+

#### Step 6: 逐步迁移到纯新格式（可选）

1. 删除API旧字段输出（一旦所有客户端都适配）
2. 删除前端兼容代码
3. 清理规范化层

**时间**: 4h | **风险**: 低 | **文件数**: 2

---

## 实施路线图

### 总体时间表

```
Week 1 (5天):
  Day 1-2: Step 1 规范化层          (4h)
  Day 2-3: Step 2 Backend双格式      (6h)
  Day 3-5: Step 3 Manager端适配      (8h)

Week 2 (5天):
  Day 1-2: Step 4 Staff端适配        (12h)
  Day 2-5: Step 5 右侧面板实现       (40h，可并行)

Week 3-4:
  测试、优化、发布                    (20h)

总计: ~90h 工作量，约 2-3 周
```

### 优先级划分

#### 🔴 高优先级（Week 1）- 基础设施

1. **定义消息类型系统**
   - 创建 `types/message.ts`，定义所有类型接口
   - 创建 `utils/messageNormalizer.ts`，实现兼容层

2. **Backend改造**
   - 双格式API输出
   - 保持向后兼容

3. **Manager端基础适配**
   - ChatMessage 支持新格式
   - 保留旧格式兼容代码

#### 🟡 中优先级（Week 1-2）- 核心功能

1. **Staff端适配**
   - 表单处理逻辑更新
   - 状态管理兼容

2. **右侧面板基础**
   - RightPanel 主容器
   - PreviewRenderer 通用渲染器
   - 激活逻辑（点击block在右侧打开）

#### 🟢 低优先级（Week 2-3）- 扩展功能

1. **各专用预览器**
   - TablePreview (recharts + react-table)
   - CodePreview (prism-react-renderer)
   - ChartPreview (recharts)
   - DocumentPreview (react-pdf-viewer)
   - ImagePreview (自写)
   - VideoPreview (html5 video)
   - DebugPreview (日志列表)

2. **优化和打磨**
   - 动画和过渡效果
   - 性能优化
   - 响应式设计

### 关键里程碑

| 里程碑 | 时间 | 验收标准 |
|--------|------|--------|
| **规范化层完成** | Day 2 | 单元测试覆盖100%，手动测试无回归 |
| **双格式API可用** | Day 3 | Backend返回新旧格式，前端正确解析 |
| **Manager端无回归** | Day 5 | 对话正常渲染，无新错误，form_card正常显示 |
| **Staff端无回归** | Day 10 | 表单提交/编辑/修改流程完整，提交成功率99%+ |
| **右侧面板MVP** | Day 14 | 可打开预览，至少3种内容类型可渲染 |
| **功能完整** | Day 20 | 所有内容类型都能预览，大多操作按钮可用 |
| **上线就绪** | Day 21 | 完整测试通过，文档齐全，可灰度发布 |

---

## 技术栈选型

### 4.1 推荐的库和方案

#### 表格预览

```javascript
// 选择: react-table + 自写 UI
// 原因: 轻量级，高度定制，不强制UI库
import { useReactTable } from '@tanstack/react-table'

// 或选择: ag-grid-react
// 原因: 功能完整，专业级表格，但依赖较重

// 不选择: 自己实现虚拟滚动
// 原因: 复杂度高，不值得
```

#### 代码编辑与高亮

```javascript
// 选择: prism-react-renderer
// 原因: 轻量级，仅提供高亮，不包含编辑器
import { Highlight, themes } from 'prism-react-renderer'

// 不选择: Monaco Editor
// 原因: 包大小28MB，过重，与需求不符

// 不选择: CodeMirror
// 原因: 相对较重，prism-react-renderer足够
```

#### 图表渲染

```javascript
// 选择: recharts
// 原因: 基于React, 轻量级, API简洁, 足够满足需求
import { BarChart, LineChart, PieChart } from 'recharts'

// 备选: echarts-for-react
// 原因: 功能更丰富，但包较大(1.5MB)，可后期按需选择

// 不选择: D3.js
// 原因: 学习曲线陡，不适合快速实现
```

#### 文件预览

```javascript
// PDF: @react-pdf-viewer/core
// 原因: React友好，轻量级，功能完整
import { Viewer } from '@react-pdf-viewer/core'

// Markdown: react-markdown
// 原因: 标准方案，与现有代码一致
import ReactMarkdown from 'react-markdown'

// 图片: 自写简单组件
// 原因: 功能简单（zoom/pan），无需第三方库
```

#### 图标按钮

```javascript
// 选择: lucide-react
// 原因: 轻量级icon库，icon质量高, TreeShakable
import { Copy, Download, Edit } from 'lucide-react'

// 不选择: @mui/icons-material
// 原因: 过重，不适合仅需少量icon的场景

// 不选择: react-icons
// 原因: 虽轻但icon库太杂，lucide更专业
```

#### 状态管理

```javascript
// 可选: zustand (推荐)
// 原因: 极轻量级，无boilerplate，完美替代Redux
import { create } from 'zustand'

// 当前: React useState + Context
// 问题: Props drilling, 复杂度高
// 迁移: 可渐进式迁移到Zustand

// 不迁移: 此次改造优先级不高
// 理由: 兼容为主，避免大改
```

### 4.2 完整依赖列表

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",

    // 图标（新增）
    "lucide-react": "^0.447",

    // Markdown 和代码高亮（已有或新增）
    "react-markdown": "^9.0",
    "remark-gfm": "^4.0",
    "prism-react-renderer": "^2.3",

    // 表格（新增）
    "@tanstack/react-table": "^8.x",

    // 图表（新增）
    "recharts": "^2.12",

    // PDF预览（新增）
    "@react-pdf-viewer/core": "^3.x",
    "pdfjs-dist": "^3.x",

    // 工具库（已有）
    "clsx": "^2.0",

    // 可选：动画库
    "framer-motion": "^10.16"
  },
  "devDependencies": {
    "@types/react-table": "^7.x"
  }
}
```

**总包大小估算**: ~500KB gzipped

### 4.3 避免的陷阱

| 库 | 问题 | 解决 |
|------|------|------|
| Monaco Editor | 28MB，过重 | 用 prism-react-renderer |
| ECharts | 1.5MB 相对较大 | 用 recharts（优先） |
| CodeMirror | 相对较重 | 用 prism-react-renderer |
| @mui (全套) | 强制Material Design | 只用图标，不用完整库 |
| Redux | boilerplate 过多 | 不迁移或用 Zustand |

---

## 常见问题

### Q1: 消息格式改了，会不会破坏现有表单功能？

**A**: 完全不会。我们采用**双格式并行**的策略：

- Backend同时输出新旧格式字段
- Frontend有规范化层，自动处理新旧格式
- Staff端的表单提交逻辑无需改动
- 旧消息格式仍然被正确识别和渲染

**验证方法**:
1. 不改代码的情况下，新API应该能被旧前端兼容
2. 新前端应该能处理旧API响应
3. 表单提交/编辑/修改流程的成功率保持99%+

### Q2: 实施过程中，Manager和Staff端需要同时更新吗？

**A**: 不需要。可以分开实施：

1. **先做Manager端**（周1）
   - 添加规范化层
   - 更新ChatMessage支持新格式
   - 保留兼容代码

2. **再做Staff端**（周2）
   - 更新App.jsx表单逻辑
   - 保留兼容代码

由于有规范化层和向后兼容代码，两个端可以独立升级，不会相互影响。

### Q3: 如果新增了一个内容类型（比如video），需要怎么改代码？

**A**: 只需要2处改动：

**1. Backend**: 返回新的block
```python
{
  "id": "video_001",
  "type": "video",
  "mimeType": "video/mp4",
  "data": { "url": "...", "duration": 120 },
  "metadata": { "actions": ["play", "download"] }
}
```

**2. Frontend**: 添加预览器
```javascript
// frontend/src/components/RightPanel/previews/VideoPreview.jsx
export function VideoPreview({ data }) {
  return <video src={data.url} controls />
}

// frontend/src/components/RightPanel/PreviewRenderer.jsx
case 'video':
  return <VideoPreview data={data} />
```

**无需改动**:
- ❌ 不需要改 ChatMessage
- ❌ 不需要改 消息格式定义（type是开放字符串）
- ❌ 不需要改 Agent定义
- ❌ 不需要改 API契约

### Q4: 右侧面板和当前的右侧栏（任务详情）怎么共存？

**A**: 采用**标签页或状态切换**设计：

```
右侧栏状态:
1. 关闭 → 仅显示展开按钮
2. 任务详情 → 显示任务信息（默认）
3. 内容预览 → 用户点击内容后切换到预览
```

或者更简洁的方案：

```
右侧栏有两个标签:
- 📋 任务 → 显示任务详情（现有逻辑）
- 👁️ 预览 → 显示内容预览（新增）

用户点击消息中的内容，自动切换到预览标签
```

### Q5: 现在已经有很多消息存储在数据库中了，旧格式怎么办？

**A**: 采用**渐进式迁移**策略：

1. **短期（保持兼容）**: 规范化层可以自动将旧格式转换为新格式，无需迁移
2. **中期（可选迁移）**: 编写脚本将历史数据转换为新格式
3. **长期（清理）**: 所有新数据都是新格式，可以删除兼容代码

**实际上**，由于有规范化层，可以一直保留兼容代码，成本很低。

### Q6: 动态按钮会不会很复杂？

**A**: 完全不复杂。就是一个简单的映射：

```javascript
// 定义icon映射
const ICON_MAP = { copy, edit, download, ... }

// 定义处理器映射
const HANDLERS = { copy: () => {...}, edit: () => {...}, ... }

// 生成按钮
{actions.map(action => (
  <button key={action} onClick={() => HANDLERS[action]()}>
    {ICON_MAP[action]}
  </button>
))}
```

新增操作按钮只需在两个映射中各加一行代码。

### Q7: 如果Agent返回的JSON格式错误会怎样？

**A**: 系统会**graceful degradation**：

1. **JSON提取失败** → 整个response当作纯文本处理（不生成block）
2. **Block格式验证失败** → 该block被忽略，其他block正常显示
3. **metadata缺失** → 预览器仍然可以显示，只是没有高级操作

**不会出现**:
- ❌ 白屏
- ❌ 错误日志刷屏
- ❌ 用户无法看到内容

---

## 附录：相关文件位置

### 需要创建的文件

```
frontend/src/
├── types/
│   └── message.ts                    # 新增：消息类型定义
├── utils/
│   └── messageNormalizer.ts          # 新增：消息规范化工具
├── components/
│   ├── RightPanel/
│   │   ├── index.jsx                 # 新增：主面板
│   │   ├── PreviewHeader.jsx         # 新增：头部
│   │   ├── PreviewContent.jsx        # 新增：内容容器
│   │   ├── PreviewRenderer.jsx       # 新增：通用渲染器
│   │   ├── previews/
│   │   │   ├── TablePreview.jsx      # 新增：表格预览
│   │   │   ├── CodePreview.jsx       # 新增：代码预览
│   │   │   ├── ChartPreview.jsx      # 新增：图表预览
│   │   │   ├── DocumentPreview.jsx   # 新增：文档预览
│   │   │   ├── ImagePreview.jsx      # 新增：图片预览
│   │   │   ├── VideoPreview.jsx      # 新增：视频预览
│   │   │   └── DebugPreview.jsx      # 新增：调试预览
│   │   └── RightPanel.css            # 新增：样式
│   ├── ChatMessage.jsx               # 修改：支持新格式
│   └── FormCardBubble.jsx            # 修改：支持block.data
└── hooks/
    └── useRightPanel.ts              # 新增：右侧栏状态管理
```

### 需要修改的文件

```
frontend/src/
├── App.jsx                           # 修改：Manager和Staff端
├── components/
│   └── ChatMessage.jsx               # 修改：支持规范化

backend/
├── app_fastapi.py                    # 修改：双格式API输出
└── agents/
    └── unified_agent.py              # 修改：JSON提取逻辑
```

---

## 总结

这个方案通过**通用ContentBlock schema** + **双格式兼容** + **规范化层**的组合，实现了：

✅ **完全向后兼容** - 旧消息格式仍然可用，无缝过渡
✅ **无限可扩展** - 新增内容类型无需改动核心逻辑
✅ **低风险迁移** - 分步实施，可随时回滚
✅ **用户体验优化** - 丰富的内容类型，动态按钮，高效交互
✅ **工程质量** - 轻量级依赖，清晰的架构，容易维护

预计完整实施时间 **2-3 周**，工作量 **~90 小时**。

---

**文档版本**: v1.0
**更新日期**: 2026-03-26
**状态**: 待实施
