# DJAgent 架构设计文档

**版本**: v2.1.0
**创建日期**: 2026-03-07
**最后更新**: 2026-03-23

---

## 一、架构概览

### 1.1 核心理念

**关键转变：**
- **从人工干预到自主规划**：SDK 的 ReAct 循环自动规划多步骤任务，无需人工编排
- **从字符串匹配到语义理解**：SDK 理解自然语言意图，自主选择工具
- **从固定流程到灵活交互**：不再预设"分析→推荐→创建"流程，用户可随时提出任何需求

### 1.2 系统整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户交互层                           │
│         (Frontend: React + WebSocket)                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Agent 会话层 (SessionManager)              │
│         - 按 user_id 缓存会话                           │
│         - 管理 Agent 生命周期                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│           Agent 核心层 (UnifiedAgent)                   │
│    - 配置驱动：Manager/Staff 两种模式                   │
│    - 基于 claude-agent-sdk 的 ReAct 循环               │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    Manager Agent   Staff Agent   (可扩展)
    (业务负责人)    (一线人员)
         │             │
         └─────────────┼─────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              SDK 接口层 (ClaudeSDKClient)               │
│    - Tool calling 和 ReAct 循环                         │
│    - 思维模式（Extended Thinking）支持                  │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
     MCP Tools     Business Skills   Data Access
     (18 个)       (6 个)            (CSV/JSON)
    ├─ 数据工具    ├─ risk_analyzer
    ├─ 文件工具    ├─ task_creator
    ├─ 任务工具    ├─ receiver_recommender
    └─ 数据库工具  ├─ summary_generator
                  ├─ 核查_guider
                  └─ hello_world
```

---

## 二、核心设计原则

### 2.1 全面拥抱 SDK

**目标**：最大化利用 SDK 的内置能力，最小化自定义代码

#### 2.1.1 工具定义机制 (@tool 装饰器)

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

# 使用 @tool 装饰器定义工具
@tool(
    name="list_users",
    description="列出系统中的用户，可按角色和部门筛选",
    input_schema={
        "type": "object",
        "properties": {
            "role": {"type": "string", "description": "用户角色"},
            "department": {"type": "string", "description": "部门"}
        }
    }
)
async def list_users_tool(args: Dict[str, Any]) -> Dict[str, Any]:
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
```

#### 2.1.2 MCP 工具命名规范 (关键！)

| 定义位置 | 命名格式 | 示例 |
|---------|---------|------|
| MCP服务器中 | `tool_name` | `list_users` |
| Agent授权时 | `mcp__server__tool_name` | `mcp__djagent_tools__list_users` |

**重要**：忽视此规则会导致"tool authorization required"错误。

```python
# ✅ 正确：allowed_tools 中使用完整格式
options = ClaudeAgentOptions(
    mcp_servers={"djagent_tools": server},
    allowed_tools=[
        "mcp__djagent_tools__list_users",      # ← mcp__ 前缀必须有
        "mcp__djagent_tools__create_task",
        "mcp__djagent_tools__parse_csv",
    ]
)
```

#### 2.1.3 SDK 的 ReAct 循环

SDK 自动处理：
- ✅ 工具调用解析和执行
- ✅ 参数验证和错误处理
- ✅ 多轮迭代规划
- ✅ 结果反馈和重新规划

**开发者只需**：
1. 定义工具和Skill
2. 设置系统提示词
3. 调用 `client.query()` 和 `client.receive_response()`

### 2.2 动态 Skill 加载

**目标**：零配置，自动发现和注册 Skill

#### 2.2.1 Skill 目录结构

```
backend/agents/skills/
├── __init__.py              # 自动扫描和注册机制
├── skill_base.py            # Skill 基类
├── skill_registry.py        # 注册中心（可选）
├── risk_analyzer/
│   ├── SKILL.md             # Skill 说明
│   └── skill.py             # 实现
├── task_creator/
│   ├── SKILL.md
│   └── skill.py
├── receiver_recommender/
│   ├── SKILL.md
│   └── skill.py
├── summary_generator/
│   ├── SKILL.md
│   └── skill.py
├── 核查_guider/
│   ├── SKILL.md
│   └── skill.py
└── hello_world/
    ├── SKILL.md
    └── skill.py
```

#### 2.2.2 Skill 基类设计

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Skill(ABC):
    """Skill 基类"""

    # 元数据
    name: str = ""
    description: str = ""
    tools: List[str] = []           # 此 Skill 需要的工具
    role: str = ""                  # Agent 角色
    responsibilities: List[str] = [] # 职责列表

    @abstractmethod
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行 Skill

        Args:
            input_data: 输入参数
            context: 上下文信息（task_id, user_id等）

        Returns:
            {"success": bool, "data": Any, "error": str}
        """
        pass

    def get_system_prompt(self) -> str:
        """生成 Skill 的 System Prompt"""
        responsibilities = "\n".join([f"- {r}" for r in self.responsibilities])
        return f"""你是{self.role}。

你的职责：
{responsibilities}

请按照以下原则工作：
1. 每个操作前获得用户确认
2. 提供清晰的步骤说明
3. 记录关键决策
"""
```

#### 2.2.3 Skill 自动加载机制

```python
# skills/__init__.py
import sys
from pathlib import Path
from typing import Dict, Any

skills_dir = Path(__file__).parent
registered_skills = {}

# 自动扫描 skills/ 目录
for skill_dir in skills_dir.iterdir():
    if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
        try:
            # 动态导入模块
            skill_name = skill_dir.name
            module = __import__(f"agents.skills.{skill_name}.skill", fromlist=[skill_name])

            # 查找 Skill 类（约定：目录名对应类名）
            class_name = ''.join(word.capitalize() for word in skill_name.split('_'))
            skill_class = getattr(module, class_name, None)

            if skill_class:
                skill_instance = skill_class()
                registered_skills[skill_instance.name] = skill_instance
        except Exception as e:
            logger.error(f"加载 Skill {skill_name} 失败: {e}")

def get_all_skills() -> Dict[str, Any]:
    """获取所有已注册的 Skill"""
    return registered_skills
```

### 2.3 配置驱动的统一 Agent 核心

**目标**：通过配置实现 Manager/Staff 两种模式，无需代码差异

#### 2.3.1 Agent 配置模型

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class AgentConfig:
    """Agent 配置"""
    mode: str                      # "manager" 或 "staff"
    user_id: str                   # 用户ID
    username: str                  # 用户名
    employee_id: str               # 工号
    allowed_tools: List[str] = field(default_factory=list)
    allowed_skills: List[str] = field(default_factory=list)
    system_prompt: Optional[str] = None
    model: str = "claude-opus-4-1-20250805"
    thinking_enabled: bool = False
    thinking_budget: int = 5000

# 使用示例
manager_config = AgentConfig(
    mode="manager",
    user_id="001",
    username="王经理",
    employee_id="EMP_001",
    allowed_tools=[
        "mcp__djagent_tools__read_risk_data",
        "mcp__djagent_tools__create_task",
        "mcp__djagent_tools__assign_task",
        # ... 18个工具
    ],
    allowed_skills=["risk_analyzer", "task_creator", "receiver_recommender"],
    thinking_enabled=True
)

staff_config = AgentConfig(
    mode="staff",
    user_id="005",
    username="刘伟",
    employee_id="EMP_005",
    allowed_tools=[
        "mcp__djagent_tools__get_task_detail",
        "mcp__djagent_tools__update_task_status",
    ],
    allowed_skills=["核查_guider", "summary_generator"],
    thinking_enabled=False
)
```

#### 2.3.2 UnifiedAgent 实现

```python
class UnifiedAgent:
    """统一 Agent 入口"""

    def __init__(self, config: AgentConfig, mcp_server, sdk_client):
        self.config = config
        self.mcp_server = mcp_server
        self.client = sdk_client

        # 根据模式选择系统提示
        if config.mode == "manager":
            self.system_prompt = self._get_manager_prompt()
        elif config.mode == "staff":
            self.system_prompt = self._get_staff_prompt()

    async def chat(self, message: str, files: List = None) -> str:
        """与 Agent 对话"""
        # SDK 自动处理 ReAct 循环
        await self.client.query(message, system=self.system_prompt)

        responses = []
        async for block in self.client.receive_response():
            if isinstance(block, TextBlock):
                responses.append(block.text)

        return "\n".join(responses)

    def _get_manager_prompt(self) -> str:
        return """你是风险管理专家，帮助业务负责人分析风险、创建任务、推荐执行人。

你的能力：
1. 分析风险数据，识别关键风险点
2. 解析和理解各种文件格式（CSV、Excel、PDF、Word）
3. 推荐最合适的执行人
4. 指导创建清晰的任务
5. 生成管理报告

工作原则：
1. 先分析，后建议
2. 任何操作前向用户展示预览
3. 等待确认后才执行关键操作
"""

    def _get_staff_prompt(self) -> str:
        return """你是一线工作助手，帮助快递员、仓管员等完成风险核查任务。

你的职责：
1. 推送任务信息，说明需要做什么
2. 指导如何进行风险核查
3. 审核提交的材料是否符合要求
4. 督促在截止时间前完成
5. 生成反馈总结

工作原则：
1. 只关注当前任务，不讨论无关话题
2. 材料不符合要求时，清楚说明缺陷
3. 给予充分的时间和支持
"""
```

### 2.4 权限控制体系

**三层权限设计**：

#### 2.4.1 第一层：身份认证
```python
# 验证用户身份（通过 employee_id）
async def verify_identity(employee_id: str) -> User:
    user = get_user_by_employee_id(employee_id)
    if not user:
        raise UnauthorizedError(f"用户 {employee_id} 不存在")
    return user
```

#### 2.4.2 第二层：角色权限
```python
# 按角色检查权限
ROLE_PERMISSIONS = {
    "总部管理员": ["view_all_tasks", "view_all_data", "manage_users"],
    "业务负责人": ["create_task", "view_own_tasks", "view_region_data"],
    "普通分析人员": ["view_own_tasks", "view_region_data"],
    "一线人员": ["view_assigned_tasks", "submit_feedback"]
}

async def check_role_permission(user: User, action: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(user.role, [])
    return action in permissions
```

#### 2.4.3 第三层：数据所有权
```python
# 按数据所有权过滤
async def filter_by_ownership(user: User, tasks: List[Task]) -> List[Task]:
    if user.employee_id == "EMP_000":  # 总部管理员
        return tasks  # 返回所有任务
    elif user.role in ["业务负责人", "普通分析人员"]:
        return [t for t in tasks if t.creator_id == user.employee_id]
    elif user.role == "一线人员":
        return [t for t in tasks if t.assigned_to_id == user.employee_id]
```

---

## 三、核心模块详解

### 3.1 Agent 架构 (agents/)

#### 3.1.1 统一 Agent 入口 (unified_agent.py)
- **职责**: 配置驱动的 Agent 实现
- **关键方法**:
  - `__init__(config, mcp_server, sdk_client)`: 初始化
  - `chat(message, files)`: 与用户对话，自动处理工具调用
  - `_process_tool_use(tool_name, input)`: 处理工具调用
  - `_handle_response()`: 处理 SDK 响应

#### 3.1.2 Manager Agent (manager_agent.py)
- **职责**: 业务负责人助手
- **核心能力**:
  1. 风险数据分析（read_risk_data 工具）
  2. 文件解析（parse_csv/excel/pdf/word 工具）
  3. 执行人推荐（receiver_recommender Skill）
  4. 任务创建指导（task_creator Skill + create_task 工具）
  5. 报告生成（summary_generator Skill）
  6. 任务查询（get_task_detail 工具）

- **关键配置**:
  ```python
  allowed_tools = [
      "mcp__djagent_tools__read_risk_data",
      "mcp__djagent_tools__query_risk_data_by_criteria",
      "mcp__djagent_tools__parse_csv",
      "mcp__djagent_tools__parse_excel",
      "mcp__djagent_tools__parse_pdf",
      "mcp__djagent_tools__parse_word",
      "mcp__djagent_tools__list_users",
      "mcp__djagent_tools__create_task",
      "mcp__djagent_tools__assign_task",
      "mcp__djagent_tools__get_task_detail",
      "mcp__djagent_tools__get_task_status",
      "mcp__djagent_tools__update_task_status",
      # ... 更多工具
  ]
  allowed_skills = ["risk_analyzer", "task_creator", "receiver_recommender", "summary_generator"]
  ```

#### 3.1.3 Staff Agent (staff_agent.py)
- **职责**: 一线人员助手
- **核心能力**:
  1. 任务推送（通过对话）
  2. 核查指导（核查_guider Skill）
  3. 文件内容验证（通过 Skill）
  4. 反馈总结生成（summary_generator Skill）
  5. 问题解答（通过自然对话）
  6. 进度督促（提醒和监督）

- **关键配置**:
  ```python
  allowed_tools = [
      "mcp__djagent_tools__get_task_detail",
      "mcp__djagent_tools__get_task_status",
      "mcp__djagent_tools__update_task_status",
      # ... 最小化工具集
  ]
  allowed_skills = ["核查_guider", "summary_generator"]
  ```

### 3.2 会话管理 (session_manager.py)

```python
class SessionManager:
    """按 user_id 缓存 Agent 会话"""

    def __init__(self):
        self.sessions = {}  # {user_id: Agent}

    async def get_or_create_manager_agent(self, user_id, user_info) -> UnifiedAgent:
        """获取或创建 Manager Agent"""
        if user_id not in self.sessions:
            config = self._build_manager_config(user_info)
            agent = UnifiedAgent(config, self.mcp_server, self.sdk_client)
            self.sessions[user_id] = agent
        return self.sessions[user_id]

    async def get_or_create_staff_agent(self, user_id, user_info) -> UnifiedAgent:
        """获取或创建 Staff Agent"""
        if user_id not in self.sessions:
            config = self._build_staff_config(user_info)
            agent = UnifiedAgent(config, self.mcp_server, self.sdk_client)
            self.sessions[user_id] = agent
        return self.sessions[user_id]
```

**重要**：
- 会话按 `employee_id` 缓存（来自 URL query 参数或 FormData）
- 刷新页面或传入不同 employee_id 会创建新会话
- 旧会话不自动清理（可配置 TTL）

### 3.3 工具系统 (tools/ + mcp_server.py)

#### 3.3.1 工具分类（18个）

**数据工具（3个）**：
- `read_risk_data`: 读取风险数据文件
- `query_data`: 通用数据查询
- `query_risk_data_by_criteria`: 按条件查询风险数据

**文件解析工具（4个）**：
- `parse_csv`: 解析 CSV 文件
- `parse_excel`: 解析 Excel 文件
- `parse_pdf`: 解析 PDF 文件
- `parse_word`: 解析 Word 文件

**用户工具（2个）**：
- `list_users`: 列出用户（支持角色、部门筛选）
- `get_user_detail`: 获取用户详情

**任务工具（5个）**：
- `create_task`: 创建任务
- `assign_task`: 分配任务
- `get_task_detail`: 获取任务详情
- `get_task_status`: 查询任务状态
- `update_task_status`: 更新任务状态

**数据库工具（2个）**：
- `list_tables`: 列出可用表
- `describe_table`: 获取表结构信息

#### 3.3.2 任务ID生成算法

```python
def generate_task_id(creator_employee_no: str) -> str:
    """
    生成任务ID

    格式: {employee_no}-{timestamp_ms}-{sequence:3d}
    示例: 001-20260323101500123-001

    - employee_no: 创建人工号 (如 001)
    - timestamp_ms: 毫秒级时间戳
    - sequence: 3位序列号，同一时间戳内递增
    """
    import time
    timestamp_ms = int(time.time() * 1000)

    # 同一毫秒内递增序列号
    if not hasattr(generate_task_id, 'sequence_map'):
        generate_task_id.sequence_map = {}

    if timestamp_ms not in generate_task_id.sequence_map:
        generate_task_id.sequence_map[timestamp_ms] = 0
    else:
        generate_task_id.sequence_map[timestamp_ms] += 1

    sequence = generate_task_id.sequence_map[timestamp_ms]
    return f"{creator_employee_no}-{timestamp_ms}-{sequence:03d}"
```

### 3.4 Skill 系统 (skills/)

#### 3.4.1 Skill 意图检测

```python
# skill_orchestrator.py 中的意图映射
_intent_mappings = {
    # risk_analyzer 意图 (风险分析)
    "分析": ["risk_analyzer"],
    "统计": ["risk_analyzer"],
    "数据": ["risk_analyzer"],
    "风险": ["risk_analyzer"],

    # task_creator 意图 (任务创建)
    "创建": ["task_creator"],
    "任务": ["task_creator"],
    "下发": ["task_creator"],
    "核查": ["task_creator"],

    # receiver_recommender 意图 (执行人推荐)
    "推荐": ["receiver_recommender"],
    "分配": ["receiver_recommender"],
    "指派": ["receiver_recommender"],

    # summary_generator 意图 (反馈总结)
    "总结": ["summary_generator"],
    "报告": ["summary_generator"],
    "汇总": ["summary_generator"],

    # 核查_guider 意图 (核查指导)
    "指导": ["核查_guider"],
    "说明": ["核查_guider"],

    # ... 55个映射
}

async def detect_intent(message: str) -> List[str]:
    """检测消息意图，返回应该使用的 Skill"""
    matched_skills = set()
    message_lower = message.lower()

    for keyword, skills in _intent_mappings.items():
        if keyword in message_lower:
            matched_skills.update(skills)

    return list(matched_skills)
```

#### 3.4.2 六个业务 Skills

1. **risk_analyzer** - 风险数据分析
   - 输入：数据、分析维度
   - 输出：统计结果、风险点识别

2. **task_creator** - 任务创建指导
   - 输入：风险描述、执行人
   - 输出：任务ID、任务详情

3. **receiver_recommender** - 执行人推荐
   - 输入：任务类型、风险等级
   - 输出：推荐人选、理由

4. **summary_generator** - 反馈总结生成
   - 输入：聊天记录、文件列表
   - 输出：反馈总结、结论

5. **核查_guider** - 核查指导
   - 输入：任务要求
   - 输出：详细指导步骤

6. **hello_world** - 演示用 Skill
   - 输入：问候
   - 输出：欢迎信息

---

## 四、数据流和工作流

### 4.1 任务创建流程

```
业务负责人
    │
    ▼
"帮我创建个风险核查任务"
    │
    ▼
Manager Agent (chat 接收)
    │
    ├─→ 意图检测：task_creator Skill
    │
    ├─→ 收集信息：
    │   - 风险数据选择
    │   - 执行人推荐
    │   - 任务描述
    │
    ├─→ 显示预览
    │   "任务预览：运单WLYD001重量异常核查..."
    │
    ├─→ 等待确认
    │   "是否确认创建？"
    │
    ├─→ create_task 工具调用
    │   生成任务ID、保存到 tasks.csv
    │
    ├─→ assign_task 工具调用
    │   分配给执行人
    │
    └─→ SSE 事件推送
        一线人员收到新任务通知
```

### 4.2 反馈完成流程

```
一线人员 (Staff Agent)
    │
    ├─→ 收到任务通知（SSE推送）
    │   "您有新任务需要核查..."
    │
    ├─→ 核查_guider Skill 指导
    │   "请按以下步骤操作..."
    │
    ├─→ 一线人员反馈
    │   - 上传文件
    │   - 说明情况
    │
    ├─→ summary_generator Skill 审核
    │   检查材料完整性和内容相关性
    │
    ├─→ 反馈完成
    │   "任务已完成，谢谢！"
    │
    ├─→ 更新任务状态
    │   status = "已完成"
    │   feedback_summary = "..."
    │
    └─→ Manager Agent 可见反馈总结
```

### 4.3 超期检测流程

```
get_tasks API 调用时
    │
    ├─→ 读取所有任务
    │
    ├─→ 遍历状态为"反馈中"的任务
    │
    ├─→ 检查：now() > feedback_deadline?
    │
    ├─→ 是：更新状态为"已超时"，记录 overdue_time
    │
    └─→ 返回任务列表
```

---

## 五、实现模式和最佳实践

### 5.1 SDK 使用模式

#### Pattern 1: 简单工具调用
```python
async def simple_tool_call():
    await client.query("列出所有用户")
    async for response in client.receive_response():
        # SDK 自动调用 list_users 工具
        # 返回用户列表
        pass
```

#### Pattern 2: 多步规划
```python
async def multi_step_planning():
    await client.query("分析今日风险数据，推荐执行人，创建核查任务")
    async for response in client.receive_response():
        # SDK 自动：
        # 1. 调用 read_risk_data 工具
        # 2. 调用 receiver_recommender Skill
        # 3. 调用 create_task 工具
        # 多步骤自动规划和执行
        pass
```

#### Pattern 3: 文件上传处理
```python
# 前端 FormData 方式
form_data = FormData()
form_data.append("message", user_message)
form_data.append("files", file_object)

# 后端接收
@app.post("/api/chat")
async def chat(
    message: str = Form(),
    user_id: str = Form(),
    files: List[UploadFile] = File(default=[])
):
    # SDK 自动调用 parse_csv/pdf/word 等工具解析文件
    pass
```

### 5.2 错误处理

#### Pattern 1: 工具执行失败
```python
@tool(name="read_risk_data")
async def read_risk_data(args: Dict) -> Dict:
    try:
        result = load_risk_data(args.get("filename"))
        return {
            "Content": [{"type": "text", "text": json.dumps(result)}],
            "is_error": False
        }
    except FileNotFoundError:
        return {
            "Content": [{"type": "text", "text": "文件不存在"}],
            "is_error": True  # ← 标记错误，Agent 会重新规划
        }
```

#### Pattern 2: Agent 对话异常
```python
async def safe_chat(message: str):
    try:
        await client.query(message)
        async for response in client.receive_response():
            yield response
    except Exception as e:
        # 降级方案：返回错误信息
        yield f"抱歉，处理出错了：{str(e)}"
```

### 5.3 性能优化

#### Pattern 1: 缓存频繁数据
```python
from functools import lru_cache
import asyncio

@lru_cache(maxsize=128)
def get_users() -> List[User]:
    """缓存用户列表，减少 CSV 读取"""
    return load_users_from_csv()

# 定期清理缓存
async def refresh_cache():
    await asyncio.sleep(3600)  # 1小时
    get_users.cache_clear()
```

#### Pattern 2: 异步 I/O
```python
# ✅ 推荐：并发处理多个工具调用
async def batch_read_files(files: List[str]) -> List[Dict]:
    tasks = [parse_file(f) for f in files]
    return await asyncio.gather(*tasks)

# ❌ 避免：串联处理（耗时）
async def serial_read_files(files: List[str]) -> List[Dict]:
    results = []
    for f in files:
        results.append(await parse_file(f))  # ← 慢
    return results
```

---

## 六、安全性和权限控制

### 6.1 权限检查流程

```
HTTP 请求
    │
    ├─→ 提取 employee_id（从 query 参数或 FormData）
    │
    ├─→ 验证用户身份
    │   是否存在于 users.csv？
    │
    ├─→ 获取用户信息
    │   role、region、department
    │
    ├─→ 检查角色权限
    │   是否有权限访问此资源？
    │
    ├─→ 检查数据所有权
    │   - 总部管理员：查看所有
    │   - 业务负责人：查看自己创建
    │   - 一线人员：查看分配给自己
    │
    └─→ 返回过滤后的数据
```

### 6.2 工具访问控制

```python
# 不同角色的工具权限不同

MANAGER_TOOLS = [
    "mcp__djagent_tools__read_risk_data",
    "mcp__djagent_tools__create_task",
    # ... 18个工具，充分权限
]

STAFF_TOOLS = [
    "mcp__djagent_tools__get_task_detail",
    "mcp__djagent_tools__update_task_status",
    # ... 最小化工具集
]

# 在 SessionManager 中根据角色初始化
if user.role in ["业务负责人", "普通分析人员"]:
    config.allowed_tools = MANAGER_TOOLS
else:
    config.allowed_tools = STAFF_TOOLS
```

---

## 七、扩展指南

### 7.1 添加新工具

```python
# 1. 在 tools/file_ops.py 中实现业务逻辑
async def export_data(task_ids: List[str]) -> str:
    # 实现导出逻辑
    pass

# 2. 在 mcp_server.py 中注册工具
@tool(
    name="export_data",
    description="导出任务数据为 CSV/Excel",
    input_schema={
        "type": "object",
        "properties": {
            "task_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "任务ID列表"
            },
            "format": {
                "type": "string",
                "enum": ["csv", "excel"],
                "description": "导出格式"
            }
        }
    }
)
async def export_data_tool(args: Dict) -> Dict:
    result = await export_data(args.get("task_ids"), args.get("format"))
    return {
        "Content": [{"type": "text", "text": result}],
        "is_error": False
    }

# 3. 在 config.py 中添加到 allowed_tools
allowed_tools = [
    # ... 现有工具
    "mcp__djagent_tools__export_data"
]
```

### 7.2 添加新 Skill

```python
# 1. 创建目录结构
backend/agents/skills/data_exporter/
├── SKILL.md
└── skill.py

# 2. 在 skill.py 中实现
from skills.skill_base import Skill

class DataExporter(Skill):
    name = "data_exporter"
    description = "导出任务数据和报告"
    role = "数据分析员"
    tools = ["mcp__djagent_tools__export_data"]
    responsibilities = [
        "按用户要求导出任务数据",
        "生成统计报告",
        "支持多种格式"
    ]

    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        # 实现 Skill 逻辑
        pass

# 3. 自动注册（无需配置）
# skills/__init__.py 会自动扫描并加载
```

---

## 八、常见问题和解决方案

### Q1: "tool authorization required" 错误

**原因**：工具名称格式不正确

**解决**：
```python
# ❌ 错误
allowed_tools = ["list_users", "create_task"]

# ✅ 正确
allowed_tools = [
    "mcp__djagent_tools__list_users",
    "mcp__djagent_tools__create_task"
]
```

### Q2: Skill 不被调用

**原因**：意图检测关键词不匹配

**解决**：
```python
# 在 skill_orchestrator.py 中添加更多关键词
_intent_mappings = {
    "分析": ["risk_analyzer"],
    "统计": ["risk_analyzer"],
    "看": ["risk_analyzer"],  # ← 添加新关键词
    "查": ["risk_analyzer"],  # ← 添加新关键词
}
```

### Q3: 权限控制不生效

**原因**：未正确提取 employee_id

**解决**：
```python
# 确保前端传递 employee_id
form_data.append("user_id", employee_id)  # ← 使用 employee_id，非 user_id

# 后端正确提取
@app.post("/api/chat")
async def chat(
    message: str = Form(),
    user_id: str = Form(),  # ← 这是 employee_id
    files: List[UploadFile] = File(default=[])
):
    # user_id 实际是 employee_id (如 EMP_001)
```

---

## 九、更新历史

**最后更新**: 2026-03-23
**文档版本**: v2.1.0

### v2.1.0 (2026-03-23)
- 整合 ARCHITECTURE_REFACTOR 和 IMPLEMENTATION_ANALYSIS 内容
- 新增详细的核心模块解析
- 新增实现模式和最佳实践
- 新增扩展指南和常见问题
- 更新了工具列表和 Skill 清单

### v2.0.0 (2026-03-07)
- 从 Manager/Staff 双类设计 → 配置驱动统一设计
- 从手动 XML 解析 → SDK 自动处理
- 从固定工作流 → ReAct 自主规划
