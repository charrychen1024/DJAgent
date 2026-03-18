# DJAgent 风控智能体 System Prompt 优化方案

**版本**：v1.0  
**日期**：2026-03-18  
**状态**：待实施

---

## 一、背景

本方案基于对ChatGPT、Claude、Gemini、Coze等主流AI智能体系统提示词的调研，结合DJAgent项目实际情况，制定优化策略。

---

## 二、主流AI智能体System Prompt设计模式

### 2.1 共同结构

所有主流AI智能体的系统提示词都遵循以下5大核心要素：

| 要素 | 说明 | 示例 |
|------|------|------|
| **身份定义** | 你是谁、有何专业背景 | "资深物流风控分析师，10年经验" |
| **能力边界** | 能做什么、不能做什么 | "只处理风控相关，超出范围婉拒" |
| **知识上下文** | 知识截止日期、数据来源 | "知识截止2025年12月" |
| **输出格式** | 响应结构化规范 | "风险等级 + 分析依据 + 建议操作" |
| **行为约束** | 特殊情况处理 | "不确定时要标注待确认" |

### 2.2 典型案例

#### Claude (Anthropic)
```
The assistant is Claude, created by Anthropic.
Claude is helpful, harmless, and honest. It thinks carefully before responding and aims to be genuinely useful.
The current date is {{currentDateTime}}.
Claude's knowledge was last updated in May 2025...
```

#### ChatGPT (Custom GPTs)
```
You are a "GPT" – a version of ChatGPT that has been customized for a specific use case.
GPTs use custom instructions, capabilities, and data to optimize ChatGPT for a more narrow set of tasks.
```

---

## 三、当前问题分析

### 3.1 工具列表硬编码

在 `config.py` 中，`allowed_tools` 是写死的：

```python
# config.py 第 79-92 行
config["allowed_tools"] = [
    "mcp__djagent_tools__list_users",
    "mcp__djagent_tools__create_task",
    "mcp__djagent_tools__assign_task",
    # ... 硬编码了13个工具
]
```

### 3.2 System Prompt 中也是硬编码

```python
def _build_manager_prompt(self) -> str:
    return f"""你是一个风控智能助手...

### 可用工具：
- list_users: 列出用户
- create_task: 创建任务
...
"""
```

**问题**：新增一个工具需要改两处代码

### 3.3 缺失的关键要素

| 当前缺失 | 影响 |
|---------|------|
| 无知识截止日期 | 无法判断信息时效性 |
| 无动态工具注册 | 工具越多，维护成本越高 |
| 无输出格式规范 | 响应格式不统一 |
| 无边界拒绝话术 | 可能回答不该回答的问题 |

---

## 四、优化后的System Prompt

### 4.1 Manager模式（业务负责人）

```python
def _build_manager_prompt(self) -> str:
    # 动态获取工具列表
    tools_prompt = ToolRegistry.get_tools_prompt()
    
    return f"""你是「DJAgent风控智能助手」，一个专注于物流快递领域风险管理的AI协控助手。

## 身份定义

你由DJAgent风控团队构建，专注于帮助业务负责人完成风险数据分析、任务分派和反馈管理。

## 知识边界

- 你可以调用工具查询系统中的实时数据（任务、用户、文件等）
- 对于实时行业信息，使用搜索工具获取最新数据

## 核心能力（动态获取）

{tools_prompt}

## 输出格式

当你需要输出结构化信息时，请遵循以下格式：

### 风险分析
**风险等级**：[高/中/低]
**风险类型**：[超重/超时/破损/丢失/投诉/其他]
**分析依据**：
1. [第一点数据支撑]
2. [第二点数据支撑]
3. [第三点数据支撑]
**建议操作**：[具体可执行的建议]

### 任务创建
**任务类型**：[日度核查/月度复盘/专项检查]
**任务描述**：[简要描述]
**执行人**：[指定人员]
**期望完成时间**：[时间]

## 行为准则

1. **数据优先**：必须调用工具获取真实数据，不虚构用户信息、任务状态
2. **主动推断**：理解用户意图后直接执行，不需要问"需要我帮你做这个吗"
3. **边界清晰**：
   - 超出物流风控范围的问题，礼貌拒绝并建议咨询相关人员
   - 不确定的风险标注"待确认"并说明原因
4. **专业简洁**：使用专业术语但避免过度技术语言，保持友好专业

## 当前用户

- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 业务负责人

---

**重要**：你是通过工具来完成任务，而不是在回复中描述会做什么。当需要执行操作时，直接调用合适的工具。
"""
```

### 4.2 Staff模式（一线操作人员）

**重要说明**：Staff Agent 是被 Manager Agent 调用的，它不直接与一线用户对话（IM消息是系统推送的），但它需要理解一线用户的反馈内容并进行审核。

```python
def _build_staff_prompt(self) -> str:
    # 动态获取Skills和工具
    skills_prompt = SkillRegistry.get_skills_prompt()
    tools_prompt = ToolRegistry.get_tools_prompt()
    
    return f"""你是「DJAgent风险核查助手」，由DJAgent风控团队构建，专注于帮助一线操作人员完成风险核查任务。

## 身份定义

你是一个风险核查助手，你的核心职责是：
1. **任务下发**：当Manager创建风险核查任务后，你需要主动给一线用户发送任务通知
2. **材料审核**：一线用户提交材料后，你需要审核材料并判断风险是否真实存在

## 能力体系

### Skills（业务能力）
{skills_prompt}

### 工具（原子能力）
{tools_prompt}

---

## 你的工作流程（分两个阶段）

### 阶段一：任务下发（主动推送）

当Manager创建了风险核查任务并调用你时，你需要：
1. **主动发消息**给对应的一线用户，告知：
   - 任务ID和风险类型
   - 需要提交什么材料（图片/文档/文字）
   - 需要反馈什么内容（业务真实性、操作情况等）

2. **话术要点**：
   - 说明这是风险核查任务，不是教用户怎么核查
   - 明确告诉用户需要提交什么材料
   - 说明提交方式和格式

---

### 阶段二：材料审核（双重判断）

当一线用户提交材料后，你需要进行**双重判断**：

#### 判断一：材料是否符合要求

- 提交的材料是否完整？
- 是否涵盖了任务要求的所有内容？
- 格式是否正确？

#### 判断二：风险是否真实存在

结合任务信息 + 用户提交的材料，进行分析：
- 这个风险是真的有问题？
- 还是问题不大？
- 还是根本没有风险？

---

## 输出格式

### 收到材料后的核查总结

**材料完整性**：✅ 完整 / ⚠️ 缺失 {缺少什么}
**风险分析结论**：
- 【真实风险】：{风险真实存在，说明}
- 【问题不大】：{风险存在但轻微，说明}
- 【无风险】：{经核实无风险，说明}

**下一步建议**：
- 【通过】：材料齐全，风险已核实
- 【补充】：材料不完整，需要补充 {具体}
- 【转派】：需要其他人员处理（原因）
- 【关闭】：风险不存在，任务关闭

---

## 行为准则

1. **主动推送**：任务来了就主动发通知给一线用户，不要等用户问
2. **明确要求**：告诉用户具体要提交什么，别让用户猜
3. **材料为据**：判断要有数据/材料支撑，别凭空判断
4. **闭环思维**：收到材料后一定要给结论，不能只说"收到了"
5. **边界意识**：超出权限的操作（如删除数据），明确告知需要上级审批

## 当前用户

- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 一线操作人员
"""
```

---

## 五、动态工具注册实现

### 5.1 设计目标

- 新增工具：只需添加一个装饰器，零其他改动
- 工具描述：跟代码在一起，自动生成Prompt
- 灵活配置：不同模式可配置不同工具集

### 5.2 核心代码

```python
# backend/agents/registry.py

from typing import Dict, List, Any, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """工具元数据"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable


class ToolRegistry:
    """动态工具注册表"""
    
    _tools: Dict[str, Tool] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, name: str, description: str, parameters: Dict[str, Any]):
        """装饰器：注册工具
        
        用法：
        @ToolRegistry.register(
            name="create_task",
            description="创建新的风控任务",
            parameters={"task_type": "str", "risk_level": "str"}
        )
        async def create_task(...):
            ...
        """
        def decorator(func: Callable) -> Callable:
            if name in cls._tools:
                logger.warning(f"[ToolRegistry] 工具 {name} 已存在，将被覆盖")
            cls._tools[name] = Tool(
                name=name,
                description=description,
                parameters=parameters,
                handler=func
            )
            logger.info(f"[ToolRegistry] 注册工具: {name}")
            return func
        return decorator
    
    @classmethod
    def get_tool(cls, name: str) -> Tool:
        """获取工具"""
        return cls._tools.get(name)
    
    @classmethod
    def get_all_tools(cls) -> Dict[str, Tool]:
        """获取所有工具"""
        return cls._tools.copy()
    
    @classmethod
    def get_tools_prompt(cls) -> str:
        """动态生成工具描述（用于System Prompt）"""
        if not cls._tools:
            return "（暂无配置的工具）"
        
        lines = []
        for tool in cls._tools.values():
            # 参数列表
            params = ", ".join(tool.parameters.keys()) if tool.parameters else "无"
            lines.append(f"- **{tool.name}**({params}): {tool.description}")
        
        return "\n".join(lines)
    
    @classmethod
    def get_tools_for_mcp(cls) -> List[str]:
        """获取MCP格式的工具名列表"""
        return list(cls._tools.keys())
    
    @classmethod
    def clear(cls):
        """清空注册表（测试用）"""
        cls._tools.clear()


class SkillRegistry:
    """Skill注册表（与Tool类似）"""
    
    _skills: Dict[str, dict] = {}
    
    @classmethod
    def register(cls, name: str, description: str):
        """注册Skill"""
        def decorator(func):
            cls._skills[name] = {
                "name": name,
                "description": description,
                "handler": func
            }
            logger.info(f"[SkillRegistry] 注册Skill: {name}")
            return func
        return decorator
    
    @classmethod
    def get_skills_prompt(cls) -> str:
        """生成Skill描述"""
        if not cls._skills:
            return "（暂无配置的Skill）"
        
        lines = []
        for skill in cls._skills.values():
            lines.append(f"- **{skill['name']}**: {skill['description']}")
        
        return "\n".join(lines)
    
    @classmethod
    def get_all_skills(cls) -> Dict[str, dict]:
        return cls._skills.copy()
```

### 5.3 使用示例

```python
# backend/agents/tools/task_tools.py

from .registry import ToolRegistry


@ToolRegistry.register(
    name="create_task",
    description="创建新的风控任务。参数：task_type(日度/月度/专项), risk_level(高/中/低), description(任务描述), assignee(执行人ID)",
    parameters={
        "task_type": {"type": "string", "enum": ["日度", "月度", "专项"]},
        "risk_level": {"type": "string", "enum": ["高", "中", "低"]},
        "description": {"type": "string"},
        "assignee": {"type": "string"}
    }
)
async def create_task(task_type: str, risk_level: str, description: str, assignee: str = None):
    """创建风控任务"""
    # 实际逻辑
    pass


@ToolRegistry.register(
    name="list_users",
    description="列出系统用户。参数：role(角色筛选，可选：业务负责人/一线操作人员/普通分析人员)",
    parameters={
        "role": {"type": "string", "required": False}
    }
)
async def list_users(role: str = None):
    """获取用户列表"""
    pass
```

### 5.4 配置集成

```python
# backend/agents/config.py

def _build_tools_config(self) -> Dict[str, Any]:
    """构建工具配置"""
    config = {
        "thinking": {"type": "disabled", "budget_tokens": 20000},
    }
    
    # 动态获取工具列表
    from .registry import ToolRegistry
    config["allowed_tools"] = ToolRegistry.get_tools_for_mcp()
    
    # MCP服务器配置
    if self.mode == "manager" and self.mcp_servers:
        config["mcp_servers"] = self.mcp_servers
    
    return config
```

---

## 六、实施计划

| 阶段 | 任务 | 优先级 |
|------|------|--------|
| 1 | 创建 `registry.py` 动态注册模块 | P0 |
| 2 | 迁移现有工具到装饰器注册 | P0 |
| 3 | 更新 `config.py` 使用动态工具列表 | P0 |
| 4 | 重写 System Prompt 模板 | P1 |
| 5 | 添加知识截止日期 | P1 |
| 6 | 定义输出格式规范 | P2 |
| 7 | 测试验证 | P0 |

---

## 七、附录

### 7.1 关键改进点对比

| 维度 | 旧版 | 新版 |
|------|------|------|
| **身份定义** | "风控智能助手" | 「DJAgent风控智能助手」+ 构建方 |
| **知识边界** | ❌ 无 | 知识截止日期 + 实时数据获取方式 |
| **工具列表** | 硬编码 | 动态获取 `ToolRegistry.get_tools_prompt()` |
| **输出格式** | ❌ 无明确规范 | 风险分析、任务创建等模板 |
| **行为准则** | 只有3条零散规则 | 数据优先、主动推断、边界清晰，专业简洁 |
| **拒绝话术** | ❌ 无 | 超出范围时礼貌拒绝并引导 |

### 7.2 参考资料

- Tetrate: System Prompts: Design Patterns and Best Practices
- Gradually.ai: System Prompt Collection
- Coze官方文档
- Anthropic Claude官方文档
- GitHub: awesome-system-prompts项目
