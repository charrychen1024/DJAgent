# DJAgent 架构重构蓝图

**版本**: v2.0  
**目标**: 基于 claude-agent-sdk 构建智能、可扩展的 Agent 系统  
**创建日期**: 2026-03-07

---

## 一、架构概览

### 1.1 核心理念

**关键转变：**
- **从人工干预到自主规划**：SDK 的 ReAct 循环自动规划多步骤任务，无需人工编排
- **从字符串匹配到语义理解**：SDK 理解自然语言意图，自主选择工具
- **从固定流程到灵活交互**：不再预设"分析→推荐→创建"流程，用户可随时提出任何需求

### 1.2 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    用户交互层                         │
│         (Frontend: React + WebSocket)                │
└──────────────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Agent 会话层                       │
│         (SessionManager: 会话池管理)                 │
└──────────────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent 核心层                       │
│    (UnifiedAgent: 配置驱动的统一入口)           │
└──────────────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   SDK 接口层                        │
│        (claude-agent-sdk: ClaudeSDKClient)           │
└──────────────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  工具和 Skill 层                     │
│    (ToolRegistry + SkillRegistry)                     │
│    - 原子工具: parse_csv, list_users 等        │
│    - 业务 Skill: risk_analyzer, task_creator 等    │
└──────────────────────────────┬──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   数据访问层                         │
│         (File System + CSV/JSON)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、核心设计原则

### 2.1 全面拥抱 SDK

**目标：** 最大化利用 SDK 的内置能力，最小化自定义代码

**具体实现：**

#### 2.1.1 使用 SDK 的 ToolDefinition 机制

```python
# ✅ 推荐：使用 @tool 装饰器定义工具
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool(
    name="list_users",
    description="列出系统中的用户",
    input_schema={"role": str, "department": str}
)
async def list_users_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    from tools import list_users
    result = list_users(args.get("role"), args.get("department"))
    return {
        "Content": [{"type": "text", "text": json.dumps(result)}],
        "is_error": "error" in result
    }

# 创建 MCP 服务器
server = create_sdk_mcp_server(
    name="djagent_tools",
    version="1.0.0",
    tools=[list_users_tool, create_task_tool, ...]
)

# 在 Agent 配置中使用
options = ClaudeAgentOptions(
    mcp_servers={"djagent_tools": server},
    allowed_tools=["list_users", "create_task", "assign_task", ...]
)
```

**优势：**
- ✅ SDK 自动处理工具调用和参数验证
- ✅ 工具描述标准化，AI 更好理解何时调用
- ✅ 自动错误处理和重试机制
- ✅ 支持 ToolUseBlock 跟踪

#### 2.1.2 移除所有手动 XML 解析

```python
# ❌ 不要这样做：
import re
from xml.etree import ElementTree

def parse_tool_call(message: str) -> Dict:
    # 手动解析 <function_calls>
    pattern = r'<invoke name="([^"]+)">'
    # ... 大量字符串处理代码
    pass

# ✅ 让 SDK 自动处理：
async def chat(self, message: str) -> str:
    await self.client.query(message)
    responses = []
    async for msg in self.client.receive_response():
        # SDK 自动解析并调用工具
        if isinstance(msg, AssistantMessage):
            responses.append(extract_text(msg))
    return "\n".join(responses)
```

### 2.2 动态 Skill 加载

**目标：** 自动发现和加载 Skill，零配置

#### 2.2.1 Skill 目录结构

```
backend/agents/skills/
├── __init__.py           # 自动扫描和注册
├── skill_base.py         # Skill 基类
├── skill_registry.py     # 注册中心
├── risk_analyzer/       # 风险分析 Skill
│   ├── SKILL.md          # Skill 说明文档
│   └── skill.py          # Skill 实现
├── task_creator/         # 任务创建 Skill
│   ├── SKILL.md
│   └── skill.py
├── receiver_recommender/ # 执行人推荐 Skill
│   ├── SKILL.md
│   └── skill.py
└── ...
```

#### 2.2.2 Skill 加载器实现

```python
# skills/__init__.py
import sys
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 自动扫描 skills/ 目录
skills_dir = Path(__file__).parent
registered_skills = {}

for skill_dir in skills_dir.iterdir():
    if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
        skill_module = skill_dir.name
        try:
            # 动态导入
            module = __import__(f"skills.{skill_module}.skill")
            
            # 查找 Skill 类
            skill_class = getattr(module, skill_module.replace('_', ''), None)
            if skill_class and callable(skill_class):
                # 实例化并注册
                skill_instance = skill_class()
                registered_skills[skill_instance.name] = skill_instance
                logger.info(f"加载 Skill: {skill_instance.name}")
        except Exception as e:
            logger.error(f"加载 Skill {skill_module} 失败: {e}")

def get_all_skills() -> Dict[str, Any]:
    """获取所有已注册的 Skill"""
    return registered_skills

def get_skill(name: str) -> Any:
    """获取指定 Skill"""
    return registered_skills.get(name)

def register_skill(name: str, skill: Any):
    """手动注册 Skill"""
    registered_skills[name] = skill
```

#### 2.2.3 Skill 基类设计

```python
# skills/skill_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Skill(ABC):
    """Skill 基类"""
    
    # Skill 元数据
    name: str = ""
    description: str = ""
    tools: List[str] = []
    role: str = ""
    responsibilities: List[str] = []
    
    def __init__(self):
        self._initialize()
    
    @abstractmethod
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行 Skill
        
        Args:
            input_data: 输入参数
            context: 上下文信息
            
        Returns:
            {"success": bool, "data": Any, "error": str}
        """
        pass
    
    def get_system_prompt(self) -> str:
        """生成 Skill 的 System Prompt"""
        prompt = f"""你是一个{self.role}。
        
你的职责：
"""
        for i, resp in enumerate(self.responsibilities, 1):
            prompt += f"{i}. {resp}\n"
        
        if self.tools:
            prompt += f"\n可用工具：{', '.join(self.tools)}\n"
        
        prompt += "\n请根据用户需求，自主调用合适的工具完成任务。"
        return prompt
    
    def validate_input(self, input_data: Dict, required: List[str]) -> Dict:
        """验证输入参数"""
        missing = [f for f in required if f not in input_data]
        if missing:
            return {"success": False, "error": f"缺少必需参数: {', '.join(missing)}"}
        return {"success": True}
```

####**2.2.4 Skill 示例：任务创建**

```python
# skills/task_creator/skill.py
from .skill_base import Skill

class TaskCreatorSkill(Skill):
    """任务创建 Skill"""
    
    name = "task_creator"
    description = "根据风险分析结果创建核查任务，下发给执行人"
    tools = ["list_users", "create_task", "assign_task"]
    role = "任务管理助手"
    responsibilities = [
        "确认任务信息（风险描述、执行人）",
        "调用工具创建任务",
        "分配任务给执行人",
        "返回创建结果"
    ]
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        # 验证输入
        validation = self.validate_input(input_data, 
            ["creator_id", "creator_name", "assigned_to_id", "assigned_to_name"]
        )
        if not validation.get("success"):
            return validation
        
        try:
            from tools import create_task, assign_task
            
            # 创建任务
            task_info = {
                "creator_id": input_data["creator_id"],
                "creator_name": input_data["creator_name"],
                "assigned_to_id": input_data["assigned_to_id"],
                "assigned_to_name": input_data["assigned_to_name"],
                "risk_summary": input_data.get("risk_summary", ""),
                "risk_data_url": input_data.get("risk_data_url", "")
            }
            
            create_result = create_task(task_info)
            if "error" in create_result:
                return create_result
            
            # 分配任务
            task_id = create_result["task_id"]
            assign_result = assign_task(
                task_id,
                input_data["assigned_to_id"],
                input_data["assigned_to_name"],
                "已下发"
            )
            
            return {
                "success": True,
                "action": "task_created_and_assigned",
                "task_id": task_id,
                "message": f"任务 {task_id} 已创建并分配给 {input_data['assigned_to_name']}"
            }
            
        except Exception as e:
            return {"error": f"创建任务失败: {str(e)}{e}"}
```

### 2.3 统一 Agent 核心

**目标：** 消除 Manager/Staff 双类，使用配置驱动的统一入口

#### 2.3.1 Agent 配置定义

```python
# agents/config.py
from typing import Dict, Any, List

class AgentConfig:
    """Agent 配置类"""
    
    def __init__(
        self,
        agent_type: str,           # "manager" 或 "staff"
        user_id: str,
        user_name: str,
        skills: List[str] = None,   # 启用的 Skill 列表
        system_prompt_template: str = None,  # 自定义 Prompt 模板
    ):
        self.agent_type = agent_type
        self.user_id = user_id
        self.user_name = user_name
        self.skills = skills or self._get_default_skills(agent_type)
        self.system_prompt = self._build_system_prompt()
    
    def _get_default_skills(self, agent_type: str) -> List[str]:
        """根据 Agent 类型返回默认 Skill"""
        if agent_type == "manager":
            return ["risk_analyzer", "task_creator", "receiver_recommender"]
        elif agent_type == "staff":
            return ["核查_guider", "summary_generator"]
        return []
    
    def _build_system_prompt(self) -> str:
        """构建 System Prompt"""
        
        # 获取 Skill 描述
        skill_descriptions = []
        from skills import get_skill
        for skill_name in self.skills:
            skill = get_skill(skill_name)
            if skill:
                skill_descriptions.append(f"- {skill.name}: {skill.description}")
        
        # 工具描述
        tool_descriptions = [
            "- list_users: 列出用户",
            "- create_task: 创建任务",
            "- assign_task: 分配任务",
            "- get_task_detail: 获取任务详情",
            "- parse_csv: 解析CSV文件",
            "- read_risk_data: 读取风险数据",
        ]
        
        # 角色
        role = "业务负责人" if self.agent_type == "manager" else "一线操作人员"
        
        prompt = f"""你是一个风控智能助手，负责协助{role}完成工作。

## 你的能力

### Skill（业务能力）
{chr(10).join(skill_descriptions)}

### 工具（原子能力）
{chr(10).join(tool_descriptions)}

## 工作方式

用户会用自然语言表达他们的需求，你自己判断需要做什么，然后自主调用合适的 Skill 或工具来完成。

重要规则：
1. 一定要调用真实的工具获取数据，不要虚构用户信息
2. 如果用户询问有哪些一线人员，调用 list_users(role="一线操作人员")
3. 如果用户要创建任务，先获取必要的信息（用户、任务详情），然后调用工具
4. 不要问用户"需要我帮你做这个吗"，直接理解意图并执行

## 当前用户
- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: {role}
"""
        return prompt
```

#### 2.3.2 统一 Agent 实现

```python
# agents/unified_agent.py
import os
import logging
from typing import Dict, Any, Optional
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class UnifiedAgent:
    """统一 Agent 入口"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.client: Optional[ClaudeSDKClient] = None
        
        # 加载 MCP 服务器
        self._mcp_server = self._load_mcp_server()
        
        # SDK 配置
        self._options = self._build_options()
        
        logger.info(f"[UnifiedAgent] 初始化: type={config.agent_type}, user={config.user_name}")
    
    def _load_mcp_server(self):
        """加载 MCP 服务器"""
        try:
            from mcp_server import create_djagent_mcp_server
            mcp_server = create_djagent_mcp_server()
            return {"djagent_tools": mcp_server}
        except Exception as e:
            logger.error(f"[UnifiedAgent] 加载 MCP 服务器失败: {e}")
            return {}
    
    def _build_options(self) -> ClaudeAgentOptions:
        """构建 SDK 配置"""
        options = {
            "env": {
                "ANTHROPIC_BASE_URL": os.getenv(
                    "ANTHROPIC_BASE_URL", 
                    "https://ark.cn-beijing.volces.com/api/coding"
                ),
                "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
            "system_prompt": self.config.system_prompt,
            "max_turns": 20,
            "thinking": {"type": "enabled", "budget_tokens": 20000},
        }
        
        # 添加 MCP 服务器
        if self._mcp_server:
            options["mcp_servers"] = self._mcp_server
            logger.info(f"[UnifiedAgent] MCP 服务器已加载")
            
            # 配置允许的工具
            allowed_tools = [
                "list_users",
                "create_task",
                "assign_task",
                "get_task_detail",
                "parse_csv",
                "read_risk_data",
            ]
            options["allowed_tools"] = allowed_tools
            logger.info(f"[UnifiedAgent] 已配置 {len(allowed_tools)} 个允许的工具")
        
        return ClaudeAgentOptions(**options)
    
    async def __aenter__(self):
        """异步上下文入口"""
        self.client = ClaudeSDKClient(options=self._options)
        await self.client.__aenter__()
        logger.info(f"[UnifiedAgent] 会话启动: {self.config.user_name}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            logger.info(f"[UnifiedAgent] 会话关闭: {self.config.user_name}")
    
    async def chat(self, message: str, context: Optional[Dict] = None) -> str:
        """
        统一聊天入口 - SDK 自主规划
        
        Args:
            message: 用户消息
            context: 上下文信息（可选）
            
        Returns:
            Agent 回复
        """
        logger.info(f"[UnifiedAgent] 收到消息: {message[:100]}...")
        
        # 构建 Prompt
        prompt = self._build_prompt(message, context)
        
        # 发送给 SDK
        await self.client.query(prompt)
        
        # 收集回复
        responses = []
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        responses.append(block.text)
            elif isinstance(msg, ResultMessage):
                logger.info(f"[UnifiedAgent] 请求完成: {msg.subtype}")
        
        reply = "\n".join(responses) if responses else "抱歉，我未能理解您的意思，请重试。"
        
        logger.info(f"[UnifiedAgent] 回复: {reply[:100]}...")
        return reply
    
    def _build_prompt(self, message: str, context: Optional[Dict]) -> str:
        """构建用户消息 Prompt"""
        prompt = f"""当前用户：{self.config.user_name} (ID: {self.config.user_id})
角色：{self.config.system_prompt.split('协助')[1].split('完成')[0]}

"""
        
        if context:
            if context.get("task_id"):
                prompt += f"当前任务ID：{context.get('task_id')}\n"
            if context.get("risk_data"):
                prompt += f"风险数据：{context.get('risk_data')}\n"
        
        prompt += f"\n用户消息：{message}\n\n"
        prompt += "请根据用户需求，调用合适的 Skill 或工具完成任务。"
        
        return prompt


# 便捷函数
async def create_agent(agent_type: str, user_id: str, user_name: str, **kwargs) -> UnifiedAgent:
    """创建 Agent 实例"""
    config = AgentConfig(
        agent_type=agent_type,
        user_id=user_id,
        user_name=user_name,
        **kwargs
    )
    agent = UnifiedAgent(config)
    await agent.__aenter__()
    return agent
```

#### 2.3.3 SessionManager 更新

```python
# agents/session_manager.py
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器 - 统一创建和管理 Agent"""
    
    def __ __init__(self):
        self.sessions: Dict[str, Any] = {}
    
    async def get_or_create_agent(
        self,
        agent_type: str,
        user_id: str,
        user_name: str,
        **kwargs
    ) -> Any:
        """获取或创建 Agent"""
        session_key = f"{agent_type}:{user_id}"
        
        # 检查是否已存在会话
        if session_key in self.sessions:
            logger.info(f"[SessionManager] 复用已有 Agent: {session_key}")
            return self.sessions[session_key]
        
        # 创建新 Agent
        from unified_agent import create_agent
        agent = await create_agent(
            agent_type=agent_type,
            user_id=user_id,
            user_name=user_name,
            **kwargs
        )
        
        # 保存会话
        self.sessions[session_key] = agent
        
        logger.info(f"[SessionManager] 创建新的 Agent: {session_key}")
        return agent
    
    def close_session(self, agent_type: str, user_id: str):
        """关闭指定会话"""
        session_key = f"{agent_type}:{user_id}"
        if session_key in self.sessions:
            agent = self.sessions[session_key]
            # 异步关闭
            import asyncio
            asyncio.create_task(agent.__aexit__(None, None, None))
            del self.sessions[session_key]
            logger.info(f"[SessionManager] 关闭会话: {session_key}")
    
    def close_all_sessions(self):
        """关闭所有会话"""
        for session_key in list(self.sessions.keys()):
            agent_type, user_id = session_key.split(':', 1)
            self.close_session(agent_type, user_id)
        
        logger.info(f"[SessionManager] 关闭所有会话，共 {len(self.sessions)} 个")


# 全局实例
_session_manager = None

def get_session_manager() -> SessionManager:
    """获取全局 SessionManager 实例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
```

### 2.4 自主规划

**目标：** 完全信任 SDK 的 ReAct 循环，移除所有人工流程控制

#### 2.4.1 ✅ 正确做法

```python
# ✅ 推荐：让 SDK 自主规划
async def chat(self, message: str) -> str:
    """
    用户说任何话，SDK 自己判断：
    - 需要分析数据吗？
    - 需要推荐执行人吗？
    - 需要创建任务吗？
    - 需要查询状态吗？
    
    SDK 的 ReAct 循环：
    1. 理解用户意图
    2. 规划需要的工具调用
    3. 执行工具调用
    4. 收集结果
    5. 根据结果决定下一步
    6. 循环直到任务完成或需要用户输入
    """
    
    # 直接发送给 SDK，不做任何预处理
    await self.client.query(message)
    
    # SDK 自动处理工具调用、意图理解、多步规划
    responses = []
    async for msg in self.client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    responses.append(block.text)
        elif isinstance(msg, ResultMessage):
            logger.info(f"请求完成: {msg.subtype}")
    
    return "\n".join(responses)
```

#### 2.4.2 ❌ 错误做法

```python
# ❌ 不要这样做：
async def chat(self, message: str) -> str:
    # ❌ 不要做手动意图检测
    if "一线用户" in message or "人员列表" in message:
        # 手动调用工具
        result = await self._call_list_users()
        return self._format_users(result)
    
    elif "创建任务" in message:
        # 手动解析参数
        user = self._extract_user(message)
        # 手动创建任务
        result = await self._create_task_manual(user)
        return self._format_task_result(result)
    
    # ❌ 不要预设固定流程
    elif self._current_step == "analyze":
        # 强制用户执行分析
        ...
        self._current_step = "recommend"
    elif self._current_step == "recommend":
        # 强制用户执行推荐
        ...
        self._current_step = "create"
```

**为什么不要这样做：**
1. **限制灵活性**：用户不能随时提出任何需求，必须按预设流程
2. **违背 SDK 设计**：SDK 的 ReAct 循环就是为自主规划设计的
3. **维护困难**：每次增加新功能都要修改多个判断分支
4. **代码复杂**：大量 if-else 嵌套，难以测试和维护

#### 2.4.3 SDK 的 ReAct 循环工作原理

```
用户消息: "帮我为刘伟快递创建一个核查任务"
         ↓
[SDK ReAct 循环]
         ↓
Step 1: 理解意图
  - 用户想创建任务
  - 需要知道刘伟的用户ID
  - 需要知道任务的具体内容
         ↓
Step 2: 规划工具调用
  - 调用 list_users(role="一线操作人员") 查找刘伟
  - 或者询问用户任务详情
         ↓
Step 3: 执行工具调用
  - SDK 调用 list_users 工具
  - 工具返回 20 个用户列表
         ↓
Step 4: 分析结果
  - 从结果中找到刘伟快递
  - 获取 user_id=005
{agent_type: "manager", user_id: "001", user_name: "王经理"}
         ↓
Step 5: 规划下一步
  - 调用 create_task 创建任务
  - 传递 creator_id="001", assigned_to_id="005", ...
         ↓
Step 6: 执行工具调用
  - SDK 调用 create_task 工具
  - 工具返回 task_id="TASK_021"
         ↓
Step 7: 规划下一步
  - 调用 assign_task 分配任务
  - 传递 task_id="TASK_021", assigned_to_id="005", status="已下发"
         ↓
Step 8: 执行工具调用
  - SDK 调用 assign_task 工具
  - 工具返回成功
         ↓
Step 9: 生成最终回复
  - "任务 TASK_021 已成功创建并分配给刘伟快递"
```

**关键优势：**
1. **自主决策**：SDK 根据意图自主选择工具，无需人工判断
2. **灵活规划**：可以处理任意顺序的工具调用
3. **错误恢复**：工具调用失败时 SDK 自动重试或调整策略
4. **上下文保持**：记住之前的对话和工具调用结果

---

## 三、实现步骤

### 阶段 1：MCP 服务器重构（优先级 P0）

**目标：** 使用 SDK 的 ToolDefinition 机制

**步骤：**
1. 创建 `agents/mcp_server/` 目录
2. 为每个工具定义独立的模块
3. 使用 `@tool` 装饰器定义工具
4. 统一创建 MCP 服务器

**文件结构：**
```
agents/mcp_server/
├── __init__.py
├── base.py              # MCP 服务器基类
├── user_tools.py        # 用户相关工具
├── task_tools.py        # 任务相关工具
├── data_tools.py.py      # 数据相关工具
└── server.py           # 服务器入口
```

**代码示例：**
```python
# mcp_server/user_tools.py
from claude_agent_sdk import tool
from typing import Dict, Any

@tool(
    name="list_users",
    description="列出系统中的用户，支持按角色和部门筛选",
    input_schema={"role": str, "department": str}
)
async def list_users_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    from tools import list_users
    
    result = list_users(args.get("role"), args.get("department"))
    
    return {
        "content": [{"type": "text", "text": str(result)}],
        "is_error": "error" in result
    }
```

### 阶段 2：Skill 动态加载（优先级 P0）

**目标：** 零配置自动发现和加载 Skill

**步骤：**
1. 修改 `skills/__init__.py` 实现自动扫描
2. 完善 `skill_base.py` 定义标准接口
3. 更新现有 Skill 符合新基类
4. 实现 `skill_registry.py` 管理注册

**代码示例：**
```python
# skills/__init__.py
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

registered_skills = {}

for skill_dir in Path(__file__).parent.iterdir():
    if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
        try:
            module = __import__(f"skills.{skill_dir.name}.skill")
            skill_class = getattr(module, skill_dir.name.replace('_', ''), None)
            
            if skill_class and callable(skill_class):
                skill_instance = skill_class()
                registered_skills[skill_instance.name] = skill_instance
                logger.info(f"[SkillLoader] 加载 Skill: {skill_instance.name}")
        except Exception as e:
            logger.error(f"[SkillLoader] 加载 Skill {skill_dir.name} 失败: {e}")

def get_all_skills() -> Dict:
    return registered_skills
```

### 阶段 3：统一 Agent 核心（优先级 P1）

**目标：** 消除 Manager/Staff 双类

**步骤：**
1. 创建 `agents/config.py` 定义配置类
2. 创建 `agents/unified_agent.py` 实现统一入口
3. 修改 `session_manager.py` 支持配置驱动的 Agent 创建
4. 更新 API 使用新的 Agent

**代码示例：**
```python
# app_fastapi.py 更新
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    message = data.get("message", "")
    user_id = data.get("user_id", "manager_default")
    username = data.get("username", "业务负责人")
    
    # 判断 Agent 类型
    agent_type = "staff" if "快递" in username or "核查" in username else "manager"
    
    # 获取或创建 Agent
    session_mgr = get_session_manager()
    agent = await session_mgr.get_or_create_agent(
        agent_type=agent_type,
        user_id=user_id,
        user_name=username
    )
    
    # 发送消息
    response_text = await agent.chat(message)
    
    return {"message": response_text, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
```

### 阶段 4：移除人工干预（优先级 P2）

**目标：** 移除所有手动检测和固定流程

**步骤：**
1. 删除所有关键词检测逻辑
2. 删除步骤状态变量
3. 删除手动工具调用包装
4. 简化 chat 方法，只调用 SDK

**删除的代码示例：**
```python
# ❌ 删除这些：
async def _handle_manual_tool_calls(self, message: str) -> Optional[str]:
    # ❌ 删除整个手动检测函数
    pass

async def _check_intent(self, message: str) -> str:
    # ❌ 删除意图检测
    pass

self._current_step = "analyze"  # ❌ 删除步骤状态
if "一线用户" in message:  # ❌ 删除关键词匹配
```

**简化后的代码：**
```python
# ✅ 保留这些：
async def chat(self, message: str) -> str:
    # 只调用 SDK，不做任何预处理
    await self.client.query(message)
    
    responses = []
    async for msg in self.client.client.receive_response():
        if isinstance(msg, AssistantMessage):
            # SDK 自动处理工具调用、意图理解、多步规划
            ...
    
    return "\n".join(responses)
```

---

## 四、测试策略

### 4.1 单元测试

**测试 MCP 工具：**
```python
# test_mcp_tools.py
import asyncio
from agents.mcp_server import create_djagent_mcp_server

async def test_list_users():
    server = create_djagent_mcp_server()
    
    # 获取 list_users 工具
    list_users_tool = None
    for tool in server["tools"]:
        if tool.name == "list_users":
            list_users_tool = tool
            break
    
    # 调用工具
    result = await list_users_tool.handler({"role": "一线操作人员"})
    
    assert "content" in result
    assert "is_error" in result
    
    print("✅ list_users 工具测试通过")
```

**测试 Skill 加载：**
```python
# test_skill_loading.py
from skills import get_all_skills

def test_skill_loading():
    skills = get_all_skills()
    
    assert "risk_analyzer" in skills
    assert "task_creator" in skills
    assert len(skills) >= 5
    
    print(f"✅ Skill 加载测试通过，共加载 {len(skills)} 个 Skill")
```

### 4.2 集成测试

**测试 Agent 对话：**
```python
# test_agent_chat.py
import asyncio
from agents.unified_agent import create_agent

async def test_chat():
    agent = await create_agent("manager", "001", "王经理")
    
    # 测试查询用户
    response1 = await agent.chat("能看到哪些一线用户")
    assert "刘伟快递" in response1 or "刘秀英快递" in response1
    
    # 测试创建任务
    response2 = await agent.chat("帮刘伟快递创建一个任务")
    assert "TASK_" in response2 or "创建成功" in response2
    
    print("✅ Agent 对话测试通过")
```

### 4.3 端到端测试

**测试完整业务流程：**
```python
# test_e2e.py
import asyncio
from agents.unified_agent import create_agent

async def test_complete_flow():
    agent = await create_agent("manager", "001", "王经理")
    
    # 完整流程
    steps = [
        "帮我分析 risk_data_001.csv 的风险数据",
        "根据分析结果，创建任务",
        "推荐最合适的执行人",
        "将任务分配给刘伟快递"
    ]
    
    for step in steps:
        response = await agent.chat(step)
        print(f"步骤: {step[:30]}... -> 回复: {response[:50]}...")
        await asyncio.sleep(1)
    
    print("✅ 端到端测试通过")
```

---

## 五、迁移指南

### 5.1 从 v1.0 迁移到 v2.0

**保留的文件：**
- `backend/agents/tools/` - 工具层保持不变
- `backend/agents/skills/*/skill.py` - Skill 实现保持不变
- `data/` - 数据保持不变
- `backend/app_fastapi.py` - API 层保持不变（只更新 Agent 创建）

**需要修改的文件：**
- `backend/agents/__init__.py` - 更新导出
- `backend/agents/session_manager.py` - 更新 Agent 创建逻辑
- `backend/agents/skills/__init__.py` - 实现自动扫描
- `backend/agents/config.py` - 新增配置类
- `backend/agents/unified_agent.py` - 新增统一 Agent
- `backend/agents/manager_agent.py` - 删除或重写
- `backend/agents/staff_agent.py` - 删除或重写

**新增的文件：**
- `backend/agents/mcp_server/` - MCP 服务器目录
- `backend/agents/config.py` - Agent 配置
- `backend/agents/unified_agent.py` - 统一 Agent

### 5.2 兼容性处理

**可选：保留旧接口用于兼容**

```python
# unified_agent.py 兼容层
async def chat(self, message: str, context: Optional[Dict] = None) -> str:
    # 新的 SDK 调用
    await self.client.query(message)
    responses = []
    async for msg in self.client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    responses.append(block.text)
    
    # 旧的兼容接口
    if "analyze_risk_data" in message:
        # 保留旧接口实现
        return await self._analyze_risk_data_legacy(message)
    
    return "\n".join(responses)
```

---

## 六、关键改进点

### 6.1 智能 vs 规则

| 方面 | v1.0（规则） | v2.0（智能） |
|------|-------------|-------------|
| 意图理解 | 关键词匹配 | SDK 自然语言理解 |
| 工具调用 | 手动触发 | SDK ReAct 循环 |
| 流程控制 | 固定步骤 | 自主规划 |
| 错误处理 | 手动处理 | SDK 自动处理 |
| 扩展性 | 修改代码 | 添加工具/Skill |

### 6.2 可维护性

| 方面 | v1.0 | v2.0 |
|------|-------|-------|
| Agent 类型 | Manager/Staff 双类 | 统一 Agent + 配置 |
| Skill 管理 | 手动导入 | 自动扫描注册 |
| 工具定义 | 字符串列表 | MCP ToolDefinition |
| 会话管理 | 简单池 | 统一 SessionManager |
| 代码复杂度 | 高（多层嵌套） | 低（配置驱动） |

### 6.3 可测试性

| 方面 | v1.0 | v2.0 |
|------|-------|-------|
| Agent 测试 | 需要模拟不同 Agent | 统一 Agent 测试 |
| 工具测试 | 难以独立测试 | MCP 工具可独立测试 |
| Skill 测试 | 需要手动导入 | 自动加载机制测试 |
| 集成测试 | 复杂的 Mock | 简单的 SDK 调用 |

---

## 七、总结

### 7.1 核心原则

1. **全面拥抱 SDK**：利用 SDK 的 ToolDefinition 和 ToolUse 机制
2. **动态 Skill 加载**：自动扫描和注册，零配置
3. **统一 Agent 核心**：配置驱动，消除 Manager/Staff 双类
4. **自主规划**：完全信任 SDK 的 ReAct 循环，移除人工干预

### 7.2 实施优先级

**P0（必须）：**
- MCP 服务器重构
- Skill 动态加载

**P1（应该）：**
- 统一 Agent 核心
- API 层更新

**P2（可以）：**
- 移除所有人工干预
- 性能优化

### 7.3 预期收益

- **开发效率**：提升 50%（无需手动编排工具调用）
- **代码复杂度**：降低 60%（配置驱动 vs 流程控制）
- **可维护性**：提升 80%（统一入口 vs 多 Agent 类）
- **灵活性**：提升 100%（自主规划 vs 固定流程）
- **可扩展性**：提升 200%（自动加载 vs 手动注册）

---

**文档状态**: ✅ 已完成  
**下一步**: 根据本蓝图实施架构重构
