# DJAgent 流式输出实现方案

## 概述

本文档记录了 DJAgent 项目实现 AI 流式输出的完整技术方案，包括后端 SSE 事件流、前端流式解析和渲染的全流程。

## 架构概览

```
┌─────────────────┐     SSE      ┌─────────────────┐         ┌─────────────────┐
│ Claude Agent    │ ──────────► │ FastAPI Backend │ ──────► │ React Frontend  │
│ SDK (流式)      │             │ (SSE 转发)      │         │ (流式渲染)      │
└─────────────────┘             └─────────────────┘         └─────────────────┘
       │                               │                           │
       ▼                               ▼                           ▼
  StreamEvent                  content_block_delta         ThinkingBlock
  - thinking_delta             content_block_start         ToolCallCard
  - text_delta                 content_block_stop          Text Block
  - input_json_delta
```

## 关键步骤

### 1. 后端：启用 SDK 流式输出

在 `backend/agents/config.py` 中配置 `include_partial_messages: True`：

```python
options = {
    "env": self.env_config,
    "system_prompt": self.system_prompt,
    "max_turns": self.max_turns,
    "cwd": str(project_root),
    "setting_sources": ["user", "project"],
    "include_partial_messages": True,  # 关键：开启流式输出
    **self.tools_config,
}
```

### 2. 后端：SSE 事件解析与转发

在 `backend/agents/sdk_message_parser.py` 中，将 SDK 的 StreamEvent 转换为 SSE 格式：

```python
from claude_agent_sdk import StreamEvent, AssistantMessage, ResultMessage

class SDKMessageParser:
    def __init__(self, message_generator):
        self.message_generator = message_generator

    async def parse(self):
        """将消息流转换为 SSE 格式"""
        has_stream_events = False

        async for msg in self.message_generator:
            if isinstance(msg, StreamEvent):
                has_stream_events = True
                event_type = msg.event.get('type', '')

                # 只处理内容相关事件
                if event_type in ['content_block_delta', 'content_block_start', 'content_block_stop']:
                    yield stream_event_to_sse(msg)

            elif isinstance(msg, AssistantMessage):
                # 避免重复：如果已有 StreamEvent，跳过 AssistantMessage
                if has_stream_events:
                    continue
                # 处理非流式响应...
```

关键函数 `stream_event_to_sse`：

```python
def stream_event_to_sse(event: StreamEvent) -> str:
    """将 StreamEvent 转换为 SSE 格式"""
    event_type = event.event.get('type', '')
    delta = event.event.get('delta', {})
    index = event.event.get('index', 0)

    # 提取 content_block 信息
    content_block = event.event.get('content_block', {})

    sse_data = {
        "type": event_type,
        "index": index,
        "delta": delta,
        "content_block": content_block
    }

    return f"event: {event_type}\ndata: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
```

### 3. 后端：流式 API 端点

在 `backend/agents/unified_agent.py` 中实现流式响应：

```python
async def stream_chat(self, message: str, user_id: str):
    """流式输出响应"""
    event_queue = asyncio.Queue()

    async def query_task():
        try:
            await self.client.query(message)
        except Exception as e:
            logger.error(f"queryTask 失败: {e}")

    async def receive_task():
        try:
            parser = SDKMessageParser(self.client.receive_response())
            async for sse_event in parser.parse():
                await event_queue.put(sse_event)
        finally:
            await event_queue.put(None)  # 结束信号

    # 并发启动
    query_coroutine = asyncio.create_task(query_task())
    receive_coroutine = asyncio.create_task(receive_task())

    # 逐个 yield 事件
    while True:
        event = await event_queue.get()
        if event is None:
            break
        yield event
```

### 4. 前端：流式响应解析

在 `frontend/src/App.jsx` 中实现 SSE 解析：

```javascript
async function processStreamingResponse(response, agentMessageId, setChatMessagesFn, setLoadingFn) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEventType = null
  let messageContent = {}  // 使用对象存储，按 block ID 索引
  let accumulatedText = ''
  let lastUpdateTime = 0
  const MIN_UPDATE_INTERVAL = 50  // 节流更新间隔

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6).trim())
          const eventData = data.delta || data
          const blockId = data.content_block?.id || `block_${data.index || 0}`

          // content_block_start - 创建新 block
          if (currentEventType === 'content_block_start') {
            const contentBlock = data.content_block || {}
            messageContent[blockId] = {
              type: contentBlock.type || 'text',
              id: blockId,
              text: '',
              thinking: '',
              name: contentBlock.name || '',
              input: contentBlock.input || {},
            }
          }

          // content_block_delta - 更新 block 内容
          if (currentEventType === 'content_block_delta') {
            if (!messageContent[blockId]) {
              messageContent[blockId] = { type: 'text', id: blockId, text: '', thinking: '' }
            }

            const targetBlock = messageContent[blockId]

            if (eventData.type === 'text_delta' && eventData.text) {
              targetBlock.text = (targetBlock.text || '') + eventData.text
              accumulatedText += eventData.text
            } else if (eventData.type === 'thinking_delta' && eventData.thinking) {
              targetBlock.thinking = (targetBlock.thinking || '') + eventData.thinking
              targetBlock.type = 'thinking'
            } else if (eventData.type === 'input_json_delta' && eventData.partial_json) {
              targetBlock.input_partial = (targetBlock.input_partial || '') + eventData.partial_json
              targetBlock.type = 'tool_use'
              try {
                targetBlock.input = JSON.parse('{' + targetBlock.input_partial + '}')
              } catch {}
            }
          }

          // 节流更新 UI
          const now = Date.now()
          if (now - lastUpdateTime >= MIN_UPDATE_INTERVAL) {
            lastUpdateTime = now
            const contentArray = Object.values(messageContent)
            setChatMessagesFn(prev => prev.map(msg => {
              if (msg.messageId === agentMessageId) {
                return { ...msg, content: contentArray, message: accumulatedText }
              }
              return msg
            }))
          }
        }
      }
    }
  } finally {
    setChatMessagesFn(prev => prev.map(msg => {
      if (msg.messageId === agentMessageId) {
        return { ...msg, isStreaming: false }
      }
      return msg
    }))
    setLoadingFn(prev => ({ ...prev, chat: false }))
  }
}
```

### 5. 前端：消息渲染组件

在 `frontend/src/components/ChatMessage.jsx` 中渲染内容块：

```javascript
const renderContentBlock = (block, index) => {
  switch (block.type) {
    case MessageBlockType.THINKING:
      return <ThinkingBlock key={`block-${index}`} thinking={block.thinking} signature={block.signature} />

    case MessageBlockType.TOOL_USE:
      return <ToolCallCard key={`block-${index}`} toolUseId={block.id} name={block.name} input={block.input} />

    case MessageBlockType.TEXT:
    default:
      return (
        <div key={`block-${index}`} className="text-block">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.text}</ReactMarkdown>
        </div>
      )
  }
}
```

## SSE 事件类型

| 事件类型 | 说明 | 前端处理 |
|---------|------|---------|
| `message_start` | 消息开始 | 重置 messageContent |
| `content_block_start` | 内容块开始 | 创建新 block |
| `content_block_delta` | 内容块增量更新 | 更新 block 内容 |
| `content_block_stop` | 内容块结束 | 标记完成 |
| `message_stop` | 消息结束 | 关闭流式状态 |

### Delta 事件类型

| Delta 类型 | 说明 | 对应组件 |
|------------|------|---------|
| `thinking_delta` | 思考过程增量 | ThinkingBlock |
| `text_delta` | 文本增量 | Text Block |
| `signature_delta` | 签名增量 | ThinkingBlock |
| `input_json_delta` | 工具参数增量 | ToolCallCard |

## 关键实现细节

### 1. 使用唯一 ID 而非数组索引

问题：SDK 会在不同阶段复用相同的 `index`（如 index 0 先用于 thinking，结束后 text 又用 index 0）。

解决方案：使用 `content_block.id` 作为唯一标识符：

```javascript
const blockId = data.content_block?.id || `block_${data.index || 0}`
messageContent[blockId] = { ... }
```

### 2. 节流更新防止过度渲染

问题：频繁的 React 状态更新会导致性能问题。

解决方案：限制更新频率（50ms）：

```javascript
const MIN_UPDATE_INTERVAL = 50
if (now - lastUpdateTime >= MIN_UPDATE_INTERVAL) {
  lastUpdateTime = now
  setChatMessagesFn(...)
}
```

### 3. 内容合并避免覆盖

问题：新 block 可能覆盖旧 block 的内容。

解决方案：每次更新时合并所有内容：

```javascript
const contentArray = Object.values(messageContent)
```

### 4. 工具结果不显示

工具执行结果（tool_result）在前端不单独显示：

```javascript
case MessageBlockType.TOOL_RESULT:
  return null;  // 隐藏工具结果
```

## 样式优化

### 思考过程 - 简约徽章样式

```css
.thinking-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--bg-primary-light);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}
```

### 工具调用 - 简约徽章样式

```css
.tool-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--bg-primary-light);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  font-size: 11px;
}
```

## 测试验证

可以通过 curl 测试后端 SSE 输出：

```bash
curl -N -X POST 'http://localhost:5005/api/chat/stream' \
  -H 'Content-Type: application/json' \
  -d '{"message": "你好", "employee_id": "000", "username": "测试"}'
```

预期输出：

```
event: message_start
data: {"type": "message_start", ...}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", ...}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "..."}}
...
```

## 文件清单

| 文件 | 作用 |
|------|------|
| `backend/agents/config.py` | 配置 `include_partial_messages: True` |
| `backend/agents/sdk_message_parser.py` | StreamEvent → SSE 转换 |
| `backend/agents/unified_agent.py` | 流式 API 端点 |
| `frontend/src/App.jsx` | 流式响应解析与状态管理 |
| `frontend/src/components/ChatMessage.jsx` | 内容块渲染 |
| `frontend/src/components/ThinkingBlock.jsx` | 思考过程组件 |
| `frontend/src/components/ToolCallCard.jsx` | 工具调用组件 |

## 参考资料

- [Anthropic Message API - Streaming](https://docs.anthropic.com/en/docs/api-reference/messages)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-sdk/overview)
- [MDN Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)