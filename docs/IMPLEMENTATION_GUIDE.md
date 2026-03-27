# 对话内容预览功能 - 详细实施指南

## 目录

1. [快速开始](#快速开始)
2. [Step-by-Step 实施指南](#step-by-step-实施指南)
3. [代码示例](#代码示例)
4. [测试策略](#测试策略)
5. [问题排查](#问题排查)

---

## 快速开始

### 前置条件

- Node.js 16+
- React 18.3+
- Python 3.9+（后端）

### 快速检查清单

```bash
# 1. 创建文件夹结构
mkdir -p frontend/src/components/RightPanel/previews
mkdir -p frontend/src/types
mkdir -p frontend/src/utils
mkdir -p frontend/src/hooks

# 2. 检查package.json中是否有必要依赖
npm list react-markdown prism-react-renderer recharts

# 3. 备份当前的App.jsx和ChatMessage.jsx
cp frontend/src/App.jsx frontend/src/App.jsx.backup
cp frontend/src/components/ChatMessage.jsx frontend/src/components/ChatMessage.jsx.backup
```

---

## Step-by-Step 实施指南

### Phase A: 基础设施（Day 1-2，预计4-6小时）

#### A1: 创建消息类型定义

**文件**: `frontend/src/types/message.ts`

```typescript
/**
 * 消息格式定义
 * 支持新旧两种格式，通过规范化层统一处理
 */

/**
 * 通用内容块
 */
export interface ContentBlock {
  // 必需
  id: string
  type: string

  // 可选
  mimeType?: string
  title?: string
  description?: string

  // 数据容器
  data: Record<string, any>

  // 渲染指引
  metadata?: {
    displayType?: 'table' | 'code' | 'chart' | 'image' | 'document' | 'video' | 'debug' | 'auto'
    height?: number
    width?: number
    previewable?: boolean
    editable?: boolean
    executable?: boolean
    downloadable?: boolean
    actions?: string[]
  }
}

/**
 * 新的统一消息格式
 */
export interface Message {
  // 基础
  timestamp: string
  sender: 'user' | 'agent' | 'system'

  // 核心内容
  content?: string        // 新标准
  message?: string        // 兼容旧格式

  // 扩展内容块
  blocks?: ContentBlock[]

  // 元数据
  metadata?: {
    agentThinking?: string
    tokensUsed?: number
    executionTime?: number
    relatedTasks?: string[]
  }

  // 向后兼容字段
  type?: string
  message_type?: string
  schema?: any
  form_id?: string
}

/**
 * 具体的Block类型定义（用于类型安全）
 */

export interface TableBlock extends ContentBlock {
  type: 'table'
  mimeType: 'application/x-table+json'
  data: {
    headers: string[]
    rows: (string | number | boolean)[][]
    summary?: string
  }
}

export interface CodeBlock extends ContentBlock {
  type: 'code'
  data: {
    code: string
    language: string
    filename?: string
    description?: string
  }
}

export interface ChartBlock extends ContentBlock {
  type: 'chart'
  data: {
    chartType: 'bar' | 'line' | 'pie' | 'scatter'
    chartConfig: any
  }
}

export interface ImageBlock extends ContentBlock {
  type: 'image'
  data: {
    url: string
    alt?: string
    width?: number
    height?: number
  }
}

export interface DocumentBlock extends ContentBlock {
  type: 'document'
  data: {
    fileType: 'pdf' | 'docx' | 'txt' | 'markdown'
    fileName: string
    fileUrl: string
    pages?: number
    size?: number
  }
}

export interface VideoBlock extends ContentBlock {
  type: 'video'
  data: {
    url: string
    duration?: number
    thumbnail?: string
  }
}

export interface DebugBlock extends ContentBlock {
  type: 'debug'
  data: {
    logs: Array<{
      timestamp: string
      level: 'info' | 'warn' | 'error' | 'debug'
      message: string
      data?: any
    }>
    metrics?: {
      duration: number
      memory: number
      cpu: number
    }
  }
}

export interface FormCardBlock extends ContentBlock {
  type: 'form_card'
  mimeType: 'application/x-form+json'
  data: any  // FormSchema
}
```

**检查点**: ✅ TypeScript编译无错误

---

#### A2: 创建规范化工具

**文件**: `frontend/src/utils/messageNormalizer.ts`

```typescript
import { Message, ContentBlock } from '../types/message'

/**
 * 规范化消息为新格式
 * - 如果已是新格式，直接返回
 * - 如果是旧格式，自动转换为新格式
 *
 * @param msg - 原始消息（可能是新格式或旧格式）
 * @returns 规范化后的消息（总是新格式）
 */
export function normalizeMessage(msg: any): Message {
  if (!msg) return null

  // 情况1: 已经是新格式（有blocks数组）
  if (msg.blocks && Array.isArray(msg.blocks) && msg.blocks.length > 0) {
    return msg as Message
  }

  // 情况2: 旧格式非文本消息（type !== 'text'）
  if (msg.type && msg.type !== 'text') {
    const block: ContentBlock = {
      id: msg.form_id || `${msg.type}_${Date.now()}`,
      type: msg.type,
      mimeType: msg.type === 'form_card' ? 'application/x-form+json' : undefined,
      title: msg.title || `${msg.type} 内容`,
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
      // 保留旧字段支持其他兼容代码
      type: msg.type,
      message: msg.message,
      schema: msg.schema,
      form_id: msg.form_id,
      message_type: msg.message_type
    } as Message
  }

  // 情况3: 纯文本消息
  return {
    timestamp: msg.timestamp,
    sender: msg.sender || 'agent',
    content: msg.message || msg.content || '',
    message: msg.message,
    blocks: []
  } as Message
}

/**
 * 反向转换：从新格式转回兼容格式（用于API调用）
 * 用于保持与旧代码的兼容性
 */
export function denormalizeMessage(msg: Message): any {
  const firstBlock = msg.blocks?.[0]

  return {
    timestamp: msg.timestamp,
    sender: msg.sender,
    message: msg.content || msg.message,
    content: msg.content,
    blocks: msg.blocks,

    // 提取block信息到顶级
    type: firstBlock?.type,
    message_type: firstBlock?.type,
    form_id: firstBlock?.id,
    schema: firstBlock?.data,
    metadata: firstBlock?.metadata
  }
}

/**
 * 批量规范化消息数组
 */
export function normalizeMessages(messages: any[]): Message[] {
  return messages.map(msg => normalizeMessage(msg)).filter(msg => msg !== null)
}

/**
 * 获取消息中的所有内容块
 */
export function getBlocksFromMessage(msg: Message): ContentBlock[] {
  return msg.blocks || []
}

/**
 * 获取指定ID的内容块
 */
export function getBlockById(msg: Message, blockId: string): ContentBlock | null {
  return msg.blocks?.find(block => block.id === blockId) || null
}

/**
 * 获取指定类型的内容块
 */
export function getBlocksByType(msg: Message, type: string): ContentBlock[] {
  return msg.blocks?.filter(block => block.type === type) || []
}
```

**检查点**: ✅ 编写单元测试验证规范化逻辑

```typescript
// frontend/src/utils/__tests__/messageNormalizer.test.ts
import { normalizeMessage, getBlockById } from '../messageNormalizer'

describe('messageNormalizer', () => {
  test('should handle new format', () => {
    const newMsg = {
      timestamp: '2026-03-26T14:30:00Z',
      sender: 'agent',
      content: 'Hello',
      blocks: [{ id: '1', type: 'text', data: {} }]
    }
    const result = normalizeMessage(newMsg)
    expect(result.blocks).toHaveLength(1)
  })

  test('should convert old format to new format', () => {
    const oldMsg = {
      timestamp: '2026-03-26T14:30:00Z',
      sender: 'agent',
      message: 'Form content',
      type: 'form_card',
      form_id: 'form_001',
      schema: { sections: [] }
    }
    const result = normalizeMessage(oldMsg)
    expect(result.blocks).toHaveLength(1)
    expect(result.blocks[0].id).toBe('form_001')
    expect(result.blocks[0].type).toBe('form_card')
  })

  test('should handle plain text message', () => {
    const textMsg = {
      timestamp: '2026-03-26T14:30:00Z',
      sender: 'user',
      message: 'Hello'
    }
    const result = normalizeMessage(textMsg)
    expect(result.blocks).toEqual([])
    expect(result.content).toBe('Hello')
  })
})
```

---

### Phase B: Backend改造（Day 2-3，预计6-8小时）

#### B1: 更新API响应格式

**文件**: `backend/app_fastapi.py` (第1100-1200行)

```python
# ============ 改动前 ============
agent_reply = {
    "timestamp": timestamp,
    "sender": "Agent",
    "message": ai_response,
    "message_type": "text",
}

# ============ 改动后 ============
# 双格式输出：既有新格式blocks，也有旧格式字段

agent_reply = {
    # 新格式（优先使用）
    "blocks": [],  # 初始化空数组

    # 旧格式（向后兼容）
    "timestamp": timestamp,
    "sender": "Agent",
    "message": ai_response,
    "message_type": "text",
    "type": "text"
}

# -------- 提取form_card JSON --------
import re
import json

agent_reply_type = "text"
agent_reply_schema = None
agent_reply_form_id = None
agent_reply_text = ai_response

# 尝试从markdown代码块中提取JSON表单定义
pattern = r'```json\s*([\s\S]*?)\s*```'
match = re.search(pattern, ai_response)

if match:
    json_text = match.group(1).strip()
    try:
        schema = json.loads(json_text)
        # 验证必需字段
        if all(key in schema for key in ['form_id', 'title', 'state', 'sections']):
            agent_reply_schema = schema
            agent_reply_form_id = schema.get('form_id')
            agent_reply_type = "form_card"
            # 移除JSON代码块，仅保留文本
            agent_reply_text = re.sub(pattern, '', ai_response).strip()
            logger.info(f"[API] 提取表单: form_id={agent_reply_form_id}")
    except json.JSONDecodeError as e:
        logger.debug(f"[API] JSON解析失败: {e}")

# -------- 构建新格式blocks --------
blocks = []

# 如果是form_card，添加form block
if agent_reply_type == "form_card":
    blocks.append({
        "id": agent_reply_form_id,
        "type": "form_card",
        "mimeType": "application/x-form+json",
        "title": agent_reply_schema.get('title', 'Form'),
        "data": agent_reply_schema,
        "metadata": {
            "editable": True,
            "actions": ["submit", "cancel", "modify"]
        }
    })

# -------- 更新agent_reply ========
agent_reply["blocks"] = blocks              # 新格式
agent_reply["message"] = agent_reply_text   # 文本部分
agent_reply["type"] = agent_reply_type      # 新格式type
agent_reply["message_type"] = agent_reply_type  # 保留旧字段

# 如果是form_card，添加兼容字段
if agent_reply_type == "form_card":
    agent_reply["schema"] = agent_reply_schema
    agent_reply["form_id"] = agent_reply_form_id
```

**检查点**: ✅ API测试验证返回格式正确

```python
# 测试：验证API返回包含新旧格式
response = await client.post('/api/chats/{chat_id}/messages', {
    'message': '生成一个表单',
    'employee_id': 'EMP_001',
    'username': 'test'
})

data = response.json()
assert 'agent_reply' in data
assert 'blocks' in data['agent_reply']       # 新格式
assert 'message' in data['agent_reply']      # 旧格式
assert 'type' in data['agent_reply']         # 兼容
```

---

### Phase C: Frontend改造 - Manager端（Day 3-5，预计8-12小时）

#### C1: 更新ChatMessage组件

**文件**: `frontend/src/components/ChatMessage.jsx`

```javascript
import React from 'react'
import PropTypes from 'prop-types'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { normalizeMessage, getBlocksByType } from '../utils/messageNormalizer'
import FormCardBubble from './FormCardBubble'
import './ChatMessage.css'

/**
 * ChatMessage - 支持新旧格式的通用消息组件
 */
const ChatMessage = ({
  message,
  onFormSubmit,
  onFormCancel,
  onFormModify,
  onBlockClick,  // 新增：内容块点击回调
  className = ''
}) => {
  if (!message) return null

  // Step 1: 规范化消息（支持新旧格式）
  const normalized = normalizeMessage(message)
  if (!normalized) return null

  const { content, blocks, sender, timestamp } = normalized

  // 格式化时间
  const formatTime = (isoString) => {
    if (!isoString) return ''
    try {
      const date = new Date(isoString)
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      return `${hours}:${minutes}`
    } catch {
      return isoString
    }
  }

  const senderLabel = sender === 'user' ? '👤 我' : sender === 'system' ? '⚙️ 系统' : '🤖 Agent'
  const baseClass = `chat-message chat-message--${sender}`

  return (
    <div className={`${baseClass} ${className}`}>
      <div className="message-header">
        <span className="message-sender">{senderLabel}</span>
        {timestamp && <span className="message-timestamp">{formatTime(timestamp)}</span>}
      </div>

      <div className="message-body">
        {/* 文本内容 */}
        {content && sender !== 'user' && (
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}

        {content && sender === 'user' && (
          <div className="text-content">{content}</div>
        )}

        {/* 新格式：内容块指示 */}
        {blocks && blocks.length > 0 && (
          <div className="blocks-indicator">
            {blocks.map(block => (
              <button
                key={block.id}
                className="block-indicator-btn"
                onClick={() => onBlockClick?.(block)}
                title={block.title || block.type}
                aria-label={`预览 ${block.title || block.type}`}
              >
                {getBlockIcon(block.type)}
                <span className="block-label">{block.title || block.type}</span>
              </button>
            ))}
          </div>
        )}

        {/* 向后兼容：旧格式form_card */}
        {!blocks && message.type === 'form_card' && message.schema && (
          <FormCardBubble
            schema={message.schema}
            onSubmit={onFormSubmit}
            onCancel={onFormCancel}
            onModify={onFormModify}
            timestamp={timestamp}
          />
        )}

        {/* 新格式：form_card block */}
        {blocks && blocks.some(b => b.type === 'form_card') && (
          <div className="form-cards">
            {getBlocksByType(normalized, 'form_card').map(block => (
              <FormCardBubble
                key={block.id}
                schema={block.data}
                onSubmit={(formData) => onFormSubmit?.(formData, block)}
                onCancel={() => onFormCancel?.(block)}
                onModify={() => onFormModify?.(block)}
                timestamp={timestamp}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 获取block类型对应的icon
 */
function getBlockIcon(type) {
  const icons = {
    'table': '📊',
    'code': '💻',
    'chart': '📈',
    'image': '🖼️',
    'document': '📄',
    'video': '🎬',
    'debug': '🔍',
    'form_card': '📋'
  }
  return icons[type] || '📦'
}

ChatMessage.propTypes = {
  message: PropTypes.object,
  onFormSubmit: PropTypes.func,
  onFormCancel: PropTypes.func,
  onFormModify: PropTypes.func,
  onBlockClick: PropTypes.func,
  className: PropTypes.string
}

export default ChatMessage
```

**检查点**: ✅ Manager端对话正常渲染，无新错误

---

### Phase C2: Manager端集成右侧面板

**文件**: `frontend/src/App.jsx` (Manager工作区)

```javascript
// 在Manager的render部分添加

const [activeBlock, setActiveBlock] = useState(null)

// 在对话消息渲染处添加
<ChatMessage
  message={msg}
  onBlockClick={(block) => {
    console.log('User clicked block:', block)
    setActiveBlock(block)
    setRightPanelOpen(true)  // 打开右侧面板
  }}
  // ... 其他回调
/>

// 右侧面板改造
{rightPanelOpen ? (
  <>
    {activeBlock ? (
      // 新增：内容预览模式
      <RightPanel
        block={activeBlock}
        onClose={() => setActiveBlock(null)}
      />
    ) : (
      // 原有：任务详情模式
      <div className="right-panel">
        {/* 现有的任务详情代码 */}
      </div>
    )}
  </>
) : (
  <button onClick={() => setRightPanelOpen(true)}>展开</button>
)}
```

---

### Phase D: Frontend改造 - Staff端（Day 5-10，预计12-16小时）

#### D1: 更新Staff端表单处理

**文件**: `frontend/src/App.jsx` (Staff工作区, 第1843行)

```javascript
// 改动前：依赖 msg.type 和 msg.form_id
{msg.type === 'form_card' && msg.schema ? (
  <FormCardBubble
    schema={msg.schema}
    onSubmit={(formData) => handleFormSubmit(msg.form_id, msg.schema, formData)}
  />
) : null}

// 改动后：规范化处理，支持新旧格式
{(() => {
  const normalized = normalizeMessage(msg)
  const formBlocks = normalized.blocks?.filter(b => b.type === 'form_card') || []

  // 新格式form block
  if (formBlocks.length > 0) {
    return formBlocks.map(block => (
      <FormCardBubble
        key={block.id}
        schema={block.data}
        onSubmit={(formData) => handleFormSubmit(block.id, block.data, formData)}
        onCancel={() => setEditingForms(prev => {
          const newState = { ...prev }
          delete newState[block.id]
          return newState
        })}
        onModify={() => setEditingForms(prev => ({ ...prev, [block.id]: true }))}
      />
    ))
  }

  // 向后兼容：旧格式form_card
  if (msg.type === 'form_card' && msg.schema) {
    return (
      <FormCardBubble
        schema={{
          ...msg.schema,
          state: editingForms[msg.form_id] ? 'editable' : 'readonly',
          actions: { showSubmit: true, showCancel: false, showModify: true }
        }}
        onSubmit={(formData) => handleFormSubmit(msg.form_id, msg.schema, formData)}
        // ...
      />
    )
  }

  return null
})()}
```

**检查点**: ✅ 表单提交/编辑/修改完整流程正常，成功率99%+

---

### Phase E: 右侧面板实现（Day 10-20，预计40+ 小时）

这部分比较长，建议分文件逐个实施。详见下面的[代码示例](#代码示例)章节。

---

## 代码示例

### 右侧面板主组件

**文件**: `frontend/src/components/RightPanel/index.jsx`

```javascript
import React, { useState } from 'react'
import { X, Maximize2 } from 'lucide-react'
import PreviewHeader from './PreviewHeader'
import PreviewRenderer from './PreviewRenderer'
import './RightPanel.css'

/**
 * RightPanel - 内容预览面板
 * 根据activeBlock自动选择合适的渲染器
 */
function RightPanel({ block, onClose, onBlockChange }) {
  const [isFullscreen, setIsFullscreen] = useState(false)

  if (!block) return null

  const { title, type, metadata, data } = block

  return (
    <div className={`right-panel ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* 头部 */}
      <PreviewHeader
        block={block}
        onClose={onClose}
        onFullscreen={() => setIsFullscreen(!isFullscreen)}
      />

      {/* 内容 */}
      <PreviewRenderer block={block} />
    </div>
  )
}

export default RightPanel
```

### 预览头部组件

**文件**: `frontend/src/components/RightPanel/PreviewHeader.jsx`

```javascript
import React from 'react'
import { X, Maximize2, Copy, Download, MoreVertical } from 'lucide-react'
import './RightPanel.css'

const ICON_MAP = {
  copy: <Copy size={18} />,
  edit: <Edit2 size={18} />,
  download: <Download size={18} />,
  export: <FileDown size={18} />,
  execute: <Play size={18} />,
  fullscreen: <Maximize2 size={18} />,
  sort: <ArrowUpDown size={18} />,
  filter: <Filter size={18} />,
  refresh: <RotateCw size={18} />,
  share: <Share2 size={18} />,
}

const ACTION_LABELS = {
  copy: '复制',
  edit: '编辑',
  download: '下载',
  export: '导出',
  execute: '运行',
  fullscreen: '全屏',
  sort: '排序',
  filter: '筛选',
  refresh: '刷新',
  share: '分享'
}

function PreviewHeader({ block, onClose, onFullscreen, onAction }) {
  const { title, metadata } = block
  const actions = metadata?.actions || []

  return (
    <div className="preview-header">
      <div className="header-left">
        <button className="close-btn" onClick={onClose} title="关闭">
          <X size={20} />
        </button>
        <h3 className="header-title">{title}</h3>
      </div>

      <div className="header-right">
        {actions.map(action => (
          <button
            key={action}
            className="icon-btn"
            title={ACTION_LABELS[action]}
            onClick={() => onAction?.(action)}
            aria-label={ACTION_LABELS[action]}
          >
            {ICON_MAP[action]}
          </button>
        ))}
        <button
          className="icon-btn fullscreen-btn"
          onClick={onFullscreen}
          title="全屏"
        >
          <Maximize2 size={18} />
        </button>
      </div>
    </div>
  )
}

export default PreviewHeader
```

### 通用预览渲染器

**文件**: `frontend/src/components/RightPanel/PreviewRenderer.jsx`

```javascript
import React, { lazy, Suspense } from 'react'
import TablePreview from './previews/TablePreview'
import CodePreview from './previews/CodePreview'
import ChartPreview from './previews/ChartPreview'
import ImagePreview from './previews/ImagePreview'
import DocumentPreview from './previews/DocumentPreview'
import './RightPanel.css'

// 动态导入其他预览器
const VideoPreview = lazy(() => import('./previews/VideoPreview'))
const DebugPreview = lazy(() => import('./previews/DebugPreview'))

/**
 * PreviewRenderer - 根据block类型自动选择渲染器
 */
function PreviewRenderer({ block }) {
  const { type, mimeType, data, metadata } = block
  const displayType = metadata?.displayType || type

  const renderPreview = () => {
    switch (displayType) {
      case 'table':
        return <TablePreview data={data} metadata={metadata} />
      case 'code':
        return <CodePreview data={data} metadata={metadata} />
      case 'chart':
        return <ChartPreview data={data} metadata={metadata} />
      case 'image':
        return <ImagePreview data={data} metadata={metadata} />
      case 'document':
        return <DocumentPreview data={data} metadata={metadata} />
      case 'video':
        return (
          <Suspense fallback={<div>Loading video...</div>}>
            <VideoPreview data={data} metadata={metadata} />
          </Suspense>
        )
      case 'debug':
        return (
          <Suspense fallback={<div>Loading logs...</div>}>
            <DebugPreview data={data} metadata={metadata} />
          </Suspense>
        )
      default:
        // 默认以JSON格式显示
        return (
          <div className="default-preview">
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </div>
        )
    }
  }

  return (
    <div className="preview-content">
      {renderPreview()}
    </div>
  )
}

export default PreviewRenderer
```

### 表格预览组件（示例）

**文件**: `frontend/src/components/RightPanel/previews/TablePreview.jsx`

```javascript
import React, { useState, useMemo } from 'react'
import { Download, Copy } from 'lucide-react'

/**
 * TablePreview - 表格预览和编辑组件
 */
function TablePreview({ data, metadata }) {
  const { headers = [], rows = [], summary = '' } = data
  const [editingCell, setEditingCell] = useState(null)
  const [tableData, setTableData] = useState(rows)

  const handleCellChange = (rowIdx, colIdx, value) => {
    const newData = [...tableData]
    newData[rowIdx] = [...newData[rowIdx]]
    newData[rowIdx][colIdx] = value
    setTableData(newData)
  }

  const handleExport = (format) => {
    if (format === 'csv') {
      const csv = [
        headers.join(','),
        ...tableData.map(row => row.join(','))
      ].join('\n')
      downloadFile(csv, 'table.csv', 'text/csv')
    }
  }

  const downloadFile = (content, filename, type) => {
    const blob = new Blob([content], { type })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="table-preview">
      {summary && <p className="table-summary">{summary}</p>}

      <div className="table-container">
        <table>
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th key={i}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableData.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, colIdx) => (
                  <td
                    key={`${rowIdx}-${colIdx}`}
                    contentEditable={metadata?.editable}
                    onBlur={(e) => {
                      if (metadata?.editable) {
                        handleCellChange(rowIdx, colIdx, e.currentTarget.textContent)
                      }
                    }}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {metadata?.editable && (
        <div className="table-actions">
          <button onClick={() => handleExport('csv')}>
            <Download size={16} /> 导出CSV
          </button>
        </div>
      )}
    </div>
  )
}

export default TablePreview
```

### 代码预览组件（示例）

**文件**: `frontend/src/components/RightPanel/previews/CodePreview.jsx`

```javascript
import React, { useState } from 'react'
import { Copy, Download, Play } from 'lucide-react'
import { Highlight, themes } from 'prism-react-renderer'

/**
 * CodePreview - 代码预览和执行组件
 */
function CodePreview({ data, metadata }) {
  const { code = '', language = 'javascript', filename = '' } = data
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `code.${language}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExecute = async () => {
    if (metadata?.executable) {
      console.log('Execute code:', code)
      // TODO: 实现代码执行逻辑
    }
  }

  return (
    <div className="code-preview">
      {filename && <div className="code-filename">{filename}</div>}

      <Highlight theme={themes.dracula} code={code} language={language}>
        {({ className, style, tokens, getLineProps, getTokenProps }) => (
          <pre className={className} style={style}>
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line, key: i })}>
                <span className="line-number">{i + 1}</span>
                {line.map((token, key) => (
                  <span key={key} {...getTokenProps({ token, key })} />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>

      <div className="code-actions">
        <button onClick={handleCopy} title={copied ? 'Copied!' : 'Copy'}>
          <Copy size={16} /> {copied ? '已复制' : '复制'}
        </button>
        <button onClick={handleDownload} title="Download">
          <Download size={16} /> 下载
        </button>
        {metadata?.executable && (
          <button onClick={handleExecute} title="Execute">
            <Play size={16} /> 运行
          </button>
        )}
      </div>
    </div>
  )
}

export default CodePreview
```

---

## 测试策略

### 单元测试

```bash
# 运行规范化工具测试
npm test messageNormalizer.test.ts

# 运行组件测试
npm test ChatMessage.test.jsx
npm test PreviewRenderer.test.jsx
```

### 集成测试

```javascript
// 测试场景1: 旧格式消息仍能正常渲染
test('should render old format message correctly', () => {
  const oldMsg = {
    timestamp: '2026-03-26T14:30:00Z',
    sender: 'agent',
    type: 'form_card',
    message: 'Please fill the form',
    schema: { sections: [] },
    form_id: 'form_001'
  }

  const { getByText } = render(<ChatMessage message={oldMsg} />)
  expect(getByText(/Please fill/)).toBeInTheDocument()
})

// 测试场景2: 新格式消息能正确显示blocks
test('should render new format message with blocks', () => {
  const newMsg = {
    timestamp: '2026-03-26T14:30:00Z',
    sender: 'agent',
    content: 'Here is the data',
    blocks: [
      { id: 'table_1', type: 'table', title: 'Data Table', data: {} }
    ]
  }

  const { getByText } = render(<ChatMessage message={newMsg} />)
  expect(getByText(/Data Table/)).toBeInTheDocument()
})

// 测试场景3: 表单提交流程不受影响
test('should submit form correctly', async () => {
  const onSubmit = jest.fn()
  const { getByText } = render(
    <FormCardBubble schema={testSchema} onSubmit={onSubmit} />
  )

  const submitBtn = getByText('提交')
  fireEvent.click(submitBtn)

  await waitFor(() => {
    expect(onSubmit).toHaveBeenCalled()
  })
})
```

### E2E测试

```gherkin
Feature: 对话内容预览

  Scenario: 显示包含表格的消息
    Given Agent返回包含表格的消息
    When 用户查看对话
    Then 消息中应显示表格指示
    And 点击表格指示时右侧面板打开
    And 表格能正确显示和编辑

  Scenario: 表单提交流程不中断
    Given 用户收到表单消息
    When 用户填写并提交表单
    Then 表单应正确提交
    And 后续消息应能正常显示
```

---

## 问题排查

### 常见问题

#### Q1: 消息规范化后，为什么还显示旧格式字段？

**A**: 这是故意的，为了保持向后兼容。normalizeMessage会同时保留旧字段，这样不兼容的代码也能使用。如果你想只用新字段，可以这样：

```javascript
const msg = normalizeMessage(rawMsg)
const { content, blocks } = msg  // 只使用新字段
// 忽略 msg.type, msg.message 等旧字段
```

#### Q2: 为什么API返回两套格式？

**A**: 这是为了平滑过渡。新旧客户端都能工作：

- 新客户端：优先使用blocks，降级使用旧字段
- 旧客户端：忽略blocks，使用旧字段

一旦所有客户端都升级，可以删除旧字段。

#### Q3: 表单提交后，form_id怎么从msg.form_id改为block.id？

**A**: 使用规范化层会自动处理。新代码应该这样写：

```javascript
// 新方式：通过规范化获取block
const normalized = normalizeMessage(msg)
const block = normalized.blocks[0]
const formId = block.id

// 或直接从block获取
onFormSubmit={(data, block) => {
  handleFormSubmit(block.id, block.data, data)
}}
```

---

**文档版本**: v1.0
**更新日期**: 2026-03-26
**状态**: 待实施
