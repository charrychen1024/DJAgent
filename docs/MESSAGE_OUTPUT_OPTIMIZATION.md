# 消息输出优化技术方案

**版本**: v1.0.0
**创建日期**: 2026-03-27
**目标**: 流式输出 + 富媒体内容

---

## 一、现状分析

### 1.1 当前实现问题

| 问题 | 当前实现 | 严重程度 |
|------|----------|----------|
| 非标准化JSON提取 | 用正则从markdown提取表单JSON | 🔴 高 |
| 无流式输出 | 收集完整消息再返回 | 🔴 高 |
| 单一文本格式 | 只支持纯文本 | 🟡 中 |
| 过度定制 | 硬编码form_id格式、JSON结构 | 🟡 中 |

### 1.2 当前代码流程

```python
# unified_agent.py - 当前实现
async for msg in self.client.receive_response():
    all_messages.append(msg)  # 收集所有消息

# 然后统一处理
for block in msg.content:
    if hasattr(block, 'text'):
        text_messages.append(block.text)

reply = "\n".join(text_messages)  # 简单拼接
```

### 1.3 表单生成当前方案（重复造轮子）

```python
# unified_agent.py:363-425
# 通过提示词约束让Agent输出JSON，然后用正则提取
notification_prompt = """...
在您的回复末尾，必须添加以下JSON格式...
```json
{{"form_id": "...", "title": "...", "sections": [...]}}
```
"""

# 然后用正则提取
pattern = r'```json\s*([\s\S]*?)\s*```'
match = re.search(pattern, reply)
form_schema = json.loads(match.group(1))
```

---

## 二、SDK官方标准能力

### 2.1 SDK已支持的标准类型

| 类型 | 状态 | 用途 |
|------|------|------|
| `AssistantMessage` | ✅ 支持 | AI响应消息 |
| `ResultMessage` | ✅ 支持 | 结果消息 |
| `TextBlock` | ✅ 支持 | 文本内容块 |
| `tool_use` | ✅ 支持 | 工具调用块 |
| 流式响应 | ✅ 支持 | `async for` 迭代 |

### 2.2 MCP协议标准返回格式

```python
# mcp_server.py - 官方标准格式
return {
    "content": [
        {
            "type": "text",
            "text": str(result)  # JSON序列化的结果
        }
    ],
    "is_error": False  # 错误标志
}
```

### 2.3 流式接口正确用法

```python
# 当前已正确使用，但未充分利用
async for msg in self.client.receive_response():
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                # 逐块处理，而非收集后统一处理
                yield block.text
```

---

## 三、优化方案

### 3.1 架构设计

```
当前流程:
用户 → 收集完整 → 统一处理 → 返回

优化后流程:
用户 → 流式迭代 → 分类型处理 → SSE推送 → 前端渲染
```

### 3.2 消息类型定义

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

class MessageType(Enum):
    TEXT = "text"           # 纯文本
    TABLE = "table"         # 表格
    CODE = "code"           # 代码块
    IMAGE = "image"        # 图片
    FORM = "form"           # 表单卡片
    LINK = "link"           # 链接
    MIXED = "mixed"         # 混合内容

@dataclass
class StreamMessage:
    type: MessageType
    content: Any             # 文本字符串/表格数据/图片URL等
    metadata: Optional[Dict[str, Any]] = None
    delta: str = ""          # 流式增量
    done: bool = False       # 是否完成
```

### 3.3 后端流式输出实现

```python
# unified_agent.py - 优化后
async def stream_chat(
    self,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    files: Optional[List[str]] = None
):
    """流式输出接口"""
    prompt = self._build_prompt(message, context, files)
    await self.client.query(prompt)

    # 流式迭代处理，而非收集后统一处理
    async for msg in self.client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                yield from self._process_block(block)
        elif isinstance(msg, ResultMessage):
            yield StreamMessage(
                type=MessageType.TEXT,
                content="",
                done=True,
                metadata={"subtype": msg.subtype}
            )

def _process_block(self, block):
    """处理内容块 - 分类输出"""
    if hasattr(block, 'text'):
        # 检测内容类型
        content_type = self._detect_content_type(block.text)
        yield StreamMessage(
            type=content_type,
            content=block.text,
            delta=block.text  # 增量内容
        )
    elif hasattr(block, 'type') and block.type == 'tool_use':
        # 工具调用 - 可以流式输出进度
        yield StreamMessage(
            type=MessageType.TEXT,
            content=f"🔧 正在调用工具: {block.name}",
            metadata={"tool": block.name, "input": block.input}
        )

def _detect_content_type(self, text: str) -> MessageType:
    """检测内容类型"""
    import re
    if re.match(r'^\|.*\|$', text.strip(), re.MULTILINE):
        return MessageType.TABLE  # Markdown表格
    elif '```' in text:
        return MessageType.CODE    # 代码块
    elif re.search(r'\[.*\]\(http', text):
        return MessageType.LINK   # 链接
    elif text.startswith('http') and any(
        text.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif']
    ):
        return MessageType.IMAGE
    return MessageType.TEXT
```

### 3.4 SSE流式推送

```python
# app_fastapi.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

@router.api_names = "/api/chat/stream")
async def chat_stream(message: str, user_id: str):
    """流式对话接口"""

    async def event_generator():
        config = create_manager_config(user_id)
        async with create_unified_agent(config) as agent:
            async for chunk in agent.stream_chat(message):
                # 转换为SSE格式
                yield f"data: {json.dumps({
                    'type': chunk.type.value,
                    'content': chunk.content,
                    'delta': chunk.delta,
                    'done': chunk.done,
                    'metadata': chunk.metadata
                })}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### 3.5 表单生成优化（MCP工具替代正则）

```python
# 不再通过提示词约束，而是在MCP工具中返回结构化数据

# mcp_server.py - 新增表单生成工具
@tool(name="generate_task_form")
async def generate_task_form(task_id: str, task_type: str) -> dict:
    """生成任务核查表单 - 返回结构化数据"""

    # 根据任务类型动态生成表单schema
    form_schema = {
        "form_id": f"form_check_{task_id[:15]}",
        "title": "核查信息收集表",
        "state": "editable",
        "sections": _build_sections_by_type(task_type)
    }

    # 返回标准MCP格式，包含结构化数据
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(form_schema)  # JSON序列化
            }
        ],
        "is_error": False
    }

# 提示词改为调用工具
notification_prompt = f"""...
请调用 generate_task_form 工具生成表单，
tool_use: {{"name": "generate_task_form", "input": {{"task_id": "{task_id}", "task_type": "{task_type}"}}}}
"""
```

---

## 四、前端渲染方案

### 4.1 消息组件架构

```
ChatMessage (根组件)
├── TextBubble       # 纯文本
├── TableBubble      # 表格渲染
├── CodeBubble      # 代码高亮
├── ImageBubble     # 图片展示
├── LinkBubble      # 链接卡片
├── FormCardBubble  # 表单卡片
└── MixedBubble     # 混合内容
```

### 4.2 流式接收示例

```jsx
// App.jsx - SSE接收
const [messages, setMessages] = useState([]);

const connectStream = (message) => {
  const eventSource = new EventSource(
    `/api/chat/stream?message=${encodeURIComponent(message)}&user_id=${userId}`
  );

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    setMessages(prev => {
      if (data.done) {
        // 消息完成
        return [...prev, { ...data, done: true }];
      }
      // 流式增量更新最后一条
      return prev.map((msg, idx) =>
        idx === prev.length - 1
          ? { ...msg, content: msg.content + data.delta }
          : msg
      );
    });
  };

  eventSource.onerror = () => eventSource.close();
};
```

### 4.3 表格渲染组件

```jsx
// components/TableBubble.jsx
import React from 'react';

export function TableBubble({ content }) {
  // 解析markdown表格为数组
  const parseTable = (md) => {
    const rows = md.trim().split('\n');
    return rows.map(row =>
      row.replace(/\|/g, '').split('|').map(cell => cell.trim())
    );
  };

  const [head, ...body] = parseTable(content);

  return (
    <table className="data-table">
      <thead>
        <tr>{head.map((cell, i) => <th key={i}>{cell}</th>)}</tr>
      </thead>
      <tbody>
        {body.map((row, i) => (
          <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

## 五、实施计划

### 5.1 阶段一：流式输出（优先级：高）

- [ ] 改造 `UnifiedAgent.chat()` 为生成器
- [ ] 新增 `/api/chat/stream` SSE端点
- [ ] 前端SSE接收和增量渲染

### 5.2 阶段二：内容类型检测（优先级：中）

- [ ] 实现 `_detect_content_type()` 方法
- [ ] 分类输出不同类型消息
- [ ] 前端按类型渲染不同组件

### 5.3 阶段三：表单标准化（优先级：中）

- [ ] 将表单生成移至MCP工具
- [ ] 移除提示词中的JSON约束
- [ ] 使用MCP标准返回格式

### 5.4 阶段四：富媒体支持（优先级：低）

- [ ] 图片上传和展示
- [ ] 链接卡片渲染
- [ ] 代码高亮显示

---

## 六、总结

### 优化前后对比

| 维度 | 当前 | 优化后 |
|------|------|--------|
| 输出方式 | 批量返回 | 流式SSE |
| 内容类型 | 纯文本 | 多类型（表格/代码/图片/表单） |
| 表单生成 | 正则提取JSON | MCP工具返回结构化数据 |
| 前端渲染 | 单一组件 | 按类型分组件渲染 |
| 标准遵循 | 自定义提示词约束 | SDK原生能力 + MCP协议 |

### 核心技术点

1. **利用SDK原生流式能力**：`async for` 已是流式，后端转SSE
2. **内容类型检测**：基于正则识别表格/代码/链接
3. **MCP标准化**：表单用工具返回，替代提示词约束
4. **前端组件化**：按类型渲染，代码更清晰
