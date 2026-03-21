# Claude Agent SDK 官方规范 vs DJAgent 实现对比分析

**更新日期**: 2026-03-21

---

## 一、官方SDK核心用法

### 1.1 基础调用方式

```python
# 方式1: query() - 简单查询
from claude_agent_sdk import query

async for message in query(prompt="What is 2 + 2?"):
    print(message)

# 方式2: ClaudeSDKClient - 持续对话
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt="You are a helpful assistant",
    max_turns=1
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Hello Claude")
    async for msg in client.receive_response():
        print(msg)
```

### 1.2 工具定义（@tool装饰器）

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeSDKClient

# 定义工具
@tool("greet", "Greet a user", {"name": str})
async def greet_user(args):
    return {
        "content": [
            {"type": "text", "text": f"Hello, {args['name']}!"}
        ]
    }

# 创建MCP服务器
server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet_user]
)

# 使用
options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__greet"]
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Greet Alice")
```

### 1.3 Hook机制

```python
from claude_agent_sdk import HookMatcher

async def check_command(input_data, tool_use_id, context):
    """在工具执行前检查"""
    if input_data["tool_name"] == "Bash":
        command = input_data["tool_input"].get("command", "")
        if "dangerous" in command:
            return {"hookSpecificOutput": {"permissionDecision": "deny"}}
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [HookMatcher(matcher="Bash", hooks=[check_command])]
    }
)
```

---

## 二、DJAgent当前实现分析

### 2.1 ✅ 符合规范的部分

| 方面 | DJAgent实现 | 状态 |
|------|------------|------|
| ClaudeSDKClient | 使用 `ClaudeSDKClient` 作为核心 | ✅ |
| ClaudeAgentOptions | 通过 `config.to_sdk_options()` 转换 | ✅ |
| 异步上下文 | 使用 `async with` 管理生命周期 | ✅ |
| System Prompt | 自定义system_prompt区分角色 | ✅ |
| 工具注册 | 手动注册到MCP服务器 | ✅ |
| 会话管理 | SessionManager管理多会话 | ✅ |

### 2.2 ⚠️ 需要改进的部分

| 方面 | DJAgent实现 | 官方推荐 | 改进建议 |
|------|------------|----------|----------|
| 工具定义 | 手动函数定义 | `@tool` 装饰器 | 使用装饰器 |
| MCP服务器 | 手动创建 | `create_sdk_mcp_server` | 采用官方方式 |
| Hook机制 | 无 | 支持PreToolUse等 | 可选引入 |
| 错误处理 | 基础try-catch | 官方异常类 | 使用SDK异常类 |
| Session恢复 | 无 | 支持session_id恢复 | 可选 |

---

## 三、具体代码对比

### 3.1 工具定义对比

**DJAgent当前方式**:
```python
# tools/data_access.py
async def read_risk_data(filename: str):
    """读取风险数据"""
    # 实现逻辑
    return {"content": [{"type": "text", "text": "..."}]}
```

**官方推荐方式**:
```python
# 使用 @tool 装饰器
@tool("read_risk_data", "读取风险数据文件", {"filename": str})
async def read_risk_data(args):
    """读取风险数据"""
    # 实现逻辑
    return {"content": [{"type": "text", "text": "..."}]}
```

### 3.2 MCP服务器创建对比

**DJAgent当前方式**:
```python
# agents/mcp_server.py
# 手动创建MCP服务器
mcp_config = {
    "name": "djagent-tools",
    "version": "1.0.0",
    "tools": {...}  # 手动传入工具字典
}
```

**官方推荐方式**:
```python
from claude_agent_sdk import create_sdk_mcp_server
from .tools import ALL_TOOLS

# 使用官方函数创建
server = create_sdk_mcp_server(
    name="djagent-tools",
    version="1.0.0",
    tools=list(ALL_TOOLS.values())  # 传入工具函数列表
)
```

### 3.3 消息处理对比

**DJAgent当前方式**:
```python
# 手动处理各种消息类型
async for msg in self.client.receive_response():
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if hasattr(block, 'text'):
                text_messages.append(block.text)
```

**官方推荐方式**:
```python
# 官方SDK v2 Session API
# 使用 send()/stream() 分离
async for message in client.stream("prompt"):
    if isinstance(message, TaskStarted):
        task_id = message.task_id
    elif isinstance(message, TaskProgress):
        progress = message.progress
```

---

## 四、改进建议

### 4.1 高优先级 - 工具定义规范化

```python
# 改进后的工具定义示例
from claude_agent_sdk import tool

@tool("create_task", "创建风险核查任务", {
    "risk_summary": str,
    "assigned_to_id": str,
    "priority": str  # "high", "medium", "low"
})
async def create_task(args):
    """创建新任务"""
    # 实现
    return {
        "content": [{
            "type": "text",
            "text": f"任务创建成功: {task_id}"
        }]
    }

@tool("list_users", "列出所有用户", {
    "role": str,  # 可选
    "region": str  # 可选
})
async def list_users(args):
    """获取用户列表"""
    # 实现
    pass
```

### 4.2 中优先级 - MCP服务器创建

```python
# 改进后的MCP服务器
from claude_agent_sdk import create_sdk_mcp_server
from .tools import (
    parse_csv, parse_excel, parse_pdf,
    read_risk_data, list_users, create_task
)

def create_djagent_server():
    """创建DJAgent MCP服务器"""
    return create_sdk_mcp_server(
        name="djagent",
        version="1.0.0",
        tools=[
            parse_csv,
            parse_excel, 
            parse_pdf,
            read_risk_data,
            list_users,
            create_task,
            # ... 其他工具
        ]
    )
```

### 4.3 可选 - Hook机制

```python
# 任务创建前检查
async def pre_create_task(input_data, tool_use_id, context):
    task_data = input_data.get("input", {})
    if not task_data.get("assigned_to_id"):
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "必须指定执行人"
            }
        }
    return {}

# 使用Hook
options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="create_task", hooks=[pre_create_task])
        ]
    }
)
```

---

## 五、官方最佳实践总结

| 方面 | 最佳实践 | DJAgent当前 |
|------|----------|-------------|
| 工具定义 | 使用 `@tool` 装饰器 | 手动函数 |
| MCP服务器 | `create_sdk_mcp_server` | 手动配置 |
| 客户端 | `ClaudeSDKClient` | ✅ 使用正确 |
| 选项配置 | `ClaudeAgentOptions` | ✅ 使用正确 |
| 错误处理 | 使用SDK异常类 | 基础try-catch |
| 会话恢复 | session_id恢复 | 无（可选） |
| Hooks | 工具调用拦截 | 无（可选） |

---

## 六、结论

DJAgent的核心架构是**符合规范**的：
- ✅ 正确使用ClaudeSDKClient
- ✅ 正确配置ClaudeAgentOptions
- ✅ 正确实现异步上下文管理

可以改进的地方：
1. **工具定义** - 采用@tool装饰器（更规范）
2. **MCP服务器** - 使用create_sdk_mcp_server（更简洁）
3. **可选** - Hook机制、错误处理、会话恢复

这些改进是**锦上添花**，不是必须的。当前实现已经可以正常工作。
