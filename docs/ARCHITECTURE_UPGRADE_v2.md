# DJAgent 智能体架构升级方案
## ——工具+Skill混合架构设计文档

**版本**: v2.0.0  
**创建日期**: 2026-03-07  
**分支**: feature/skill-based-agent

---

## 一、升级目标

### 1.1 当前问题

| 问题 | 现状 | 期望 |
|------|------|------|
| 对话灵活性差 | 预设流程，固定环节 | 用户随意表达，AI自主理解 |
| 工具调用生硬 | 人工判断意图，显式调用 | SDK自主判断，动态调用 |
| 扩展性差 | 新功能需改核心代码 | 新Skill即插即用 |
| 维护性差 | 业务逻辑散各处 | 业务逻辑封装在Skill中 |

### 1.2 升级目标

- **灵活性**：用户可以用自然语言表达任意目标
- **自主性**：SDK自主理解意图并调用工具/Skill
- **可扩展性**：新增业务能力只需添加Skill
- **可维护性**：业务逻辑封装，代码结构清晰

---

## 二、整体架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                           │
│         (React前端 - 保持不变，仅调整Agent调用)              │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Agent层（保持入口）                     │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              ManagerAgent / StaffAgent               │  │
│  │   - 统一chat()入口                                   │  │
│  │   - 注册Skill + 工具                                  │  │
│  │   - SDK自主路由                                      │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Skill层      │ │    Skill层      │ │    Skill层      │
│  风险分析Skill  │ │ 任务创建Skill   │ │ 核查指导Skill   │
│  (业务封装)     │ │  (业务封装)     │ │  (业务封装)     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       工具层（原子能力）                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │文件解析器 │ │ 数据读写  │ │ 文件操作  │ │ 任务管理  │    │
│  │(原子工具) │ │ (原子工具)│ │ (原子工具)│ │ (原子工具)│    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       数据存储层                            │
│    CSV文件(用户/任务/风险数据) + JSON文件(反馈/上传)        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
backend/agents/
├── tools/                      # 工具层（原子能力）
│   ├── __init__.py
│   ├── file_parser.py          # 文件解析工具
│   │   ├── parse_csv()
│   │   ├── parse_excel()
│   │   ├── parse_pdf()
│   │   └── parse_word()
│   │
│   ├── data_access.py          # 数据访问工具
│   │   ├── read_risk_data()
│   │   ├── list_users()
│   │   ├── get_task()
│   │   └── get_task_detail()
│   │
│   ├── task_manager.py         # 任务管理工具
│   │   ├── create_task()
│   │   ├── update_task_status()
│   │   └── query_tasks()
│   │
│   └── file_ops.py             # 文件操作工具
│       ├── save_uploaded_file()
│       └── read_file_content()
│
├── skills/                     # Skill层（业务能力）
│   ├── __init__.py
│   ├── skill_registry.py       # Skill注册中心
│   │
│   ├── risk_analyzer/          # 风险分析Skill
│   │   ├── SKILL.md            # Skill定义
│   │   └── skill.py            # Skill实现
│   │
│   ├── task_creator/          # 任务创建Skill
│   │   ├── SKILL.md
│   │   └── skill.py
│   │
│   ├── receiver_recommender/  # 推荐执行人Skill
│   │   ├── SKILL.md
│   │   └── skill.py
│   │
│   ├──核查_guider/            # 核查指导Skill
│   │   ├── SKILL.md
│   │   └── skill.py
│   │
│   └── summary_generator/      # 总结生成Skill
│       ├── SKILL.md
│       └── skill.py
│
├── manager_agent.py            # 主智能体（重构）
├── staff_agent.py              # 子智能体（重构）
├── session_manager.py          # 会话管理
└── agent_factory.py            # Agent工厂
```

---

## 三、工具层设计

### 3.1 工具原则

- **原子化**：每个工具只做一件事
- **通用性**：不包含业务逻辑
- **可复用**：多个Skill可共用

### 3.2 文件解析工具 (file_parser.py)

```python
"""
文件解析工具 - 原子化
只负责解析文件，不包含业务逻辑
"""

def parse_csv(file_path: str) -> Dict[str, Any]:
    """解析CSV文件"""
    # 实现...
    
def parse_excel(file_path: str, sheet_name: str = None) -> Dict[str, Any]:
    """解析Excel文件"""
    # 实现...
    
def parse_pdf(file_path: str, max_pages: int = 3) -> Dict[str, Any]:
    """解析PDF文件"""
    # 实现...
    
def parse_word(file_path: str) -> Dict[str, Any]:
    """解析Word文件"""
    # 实现...
```

### 3.3 数据访问工具 (data_access.py)

```python
"""
数据访问工具 - 原子化
只负责数据读写，不包含业务逻辑
"""

def read_risk_data(filename: str) -> Dict[str, Any]:
    """读取风险数据"""
    
def list_users(role: str = None) -> Dict[str, Any]:
    """列出用户"""
    
def get_task(task_id: str) -> Dict[str, Any]:
    """获取任务"""
    
def get_task_detail(task_id: str) -> Dict[str, Any]:
    """获取任务详情含反馈"""
```

### 3.4 任务管理工具 (task_manager.py)

```python
"""
任务管理工具 - 原子化
只负责任务CRUD，不包含业务逻辑
"""

def create_task(task_info: Dict) -> Dict[str, Any]:
    """创建任务"""
    # 生成task_id
    # 写入tasks.csv
    # 返回结果
    
def update_task_status(task_id: str, status: str, summary: str = "") -> Dict[str, Any]:
    """更新任务状态"""
    
def query_tasks(filters: Dict = None) -> Dict[str, Any]:
    """查询任务列表"""
```

### 3.5 文件操作工具 (file_ops.py)

```python
"""
文件操作工具 - 原子化
只负责文件存取，不包含业务逻辑
"""

def save_uploaded_file(task_id: str, file_data: bytes, filename: str) -> Dict[str, Any]:
    """保存上传文件"""
    
def read_file_content(file_path: str) -> Dict[str, Any]:
    """读取文件内容"""
```

---

## 四、Skill层设计

### 4.1 Skill原则

- **业务化**：封装完整业务流程
- **场景化**：针对特定业务场景
- **可组合**：可调用多个工具

### 4.2 SKILL.md 规范

```yaml
# skills/{skill_name}/SKILL.md
name: {Skill名称}
description: {Skill描述}

# Skill可以使用哪些工具
tools:
  - parse_csv
  - list_users
  - create_task
  # ...

# 提示词模板
prompts:
  # 主流程提示词
  main: |
    你是一个{Skill角色}。你的职责是：
    1. {职责1}
    2. {职责2}
    
    当前上下文：
    {context}
    
    用户输入：
    {user_input}
    
    请处理并返回结果。
    
  # 可选：子流程提示词
  sub_process: |
    ...

# 输入输出定义
inputs:
  - name: user_message
    type: string
    required: true
  - name: context
    type: object
    required: false

outputs:
  - name: result
    type: string
    description: 处理结果
  - name: action_taken
    type: string
    description: 执行的动作
```

### 4.3 Skill实现基类

```python
# skills/skill_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Skill(ABC):
    """Skill基类"""
    
    name: str = ""           # Skill名称
    description: str = ""   # Skill描述
    tools: List[str] = []    # 使用的工具列表
    prompts: Dict[str, str] = {}  # 提示词模板
    
    @abstractmethod
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """执行Skill"""
        pass
    
    def get_system_prompt(self) -> str:
        """获取System Prompt"""
        return self.prompts.get("main", "")
```

### 4.4 各Skill详细设计

#### 4.4.1 风险分析Skill (risk_analyzer)

```yaml
# skills/risk_analyzer/SKILL.md
name: 风险数据分析
description: 分析风险数据，识别风险模式，提供决策建议

tools:
  - parse_csv
  - parse_excel
  - read_risk_data
  - list_users

prompts:
  main: |
    你是一个资深风控专家。
    
    用户希望分析风险数据，你需要：
    1. 解析用户提供的数据
    2. 识别风险模式（超时、重量异常、虚假签收等）
    3. 分析异常特征
    4. 给出风险等级建议
    
    数据：{data}
    用户问题：{question}
    
    请提供专业的分析报告。
```

```python
# skills/risk_analyzer/skill.py
from .skill_base import Skill
from ..tools.file_parser import parse_csv, parse_excel
from ..tools.data_access import list_users

class RiskAnalyzerSkill(Skill):
    name = "risk_analyzer"
    description = "分析风险数据，识别风险模式"
    tools = ["parse_csv", "parse_excel", "read_risk_data", "list_users"]
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        # 1. 获取数据
        # 2. 调用解析工具
        # 3. 调用AI分析
        # 4. 返回结果
```

#### 4.4.2 任务创建Skill (task_creator)

```yaml
# skills/task_creator/SKILL.md
name: 任务创建与管理
description: 根据风险分析结果创建核查任务，下发给执行人

tools:
  - list_users
  - create_task
  - update_task_status

prompts:
  main: |
    你是一个任务管理助手。
    
    用户希望你创建任务，你需要：
    1. 确认任务信息（风险描述、执行人）
    2. 调用工具创建任务
    3. 返回创建结果
    
    当前信息：{task_info}
    
    请执行任务创建。
```

#### 4.4.3 推荐执行人Skill (receiver_recommender)

```yaml
# skills/receiver_recommender/SKILL.md
name: 推荐执行人
description: 根据风险特征和执行人情况，推荐最合适的核查人员

tools:
  - list_users
  - get_task_detail

prompts:
  main: |
    你是一个人员推荐专家。
    
    根据以下风险数据和可选执行人，推荐最合适的人选：
    
    风险数据：{risk_data}
    可选执行人：{users}
    
    请考虑：
    1. 执行人所在区域与风险地点的关系
    2. 执行人的历史任务完成情况
    3. 执行人对该类风险的熟悉程度
    
    返回推荐人及理由。
```

#### 4.4.4 核查指导Skill (核查_guider)

```yaml
# skills/核查_guider/SKILL.md
name: 核查指导
description: 指导一线人员完成风险核查工作

tools:
  - get_task_detail
  - parse_pdf
  - parse_word

prompts:
  main: |
    你是一个核查指导专家。
    
    当前任务信息：{task_info}
    用户问题：{question}
    
    请提供：
    1. 任务详细要求
    2. 核查步骤指导
    3. 需要准备的材料
    4. 注意事项
    
    请用友好、专业的语气指导用户完成核查。
```

#### 4.4.5 总结生成Skill (summary_generator)

```yaml
# skills/summary_generator/SKILL.md
name: 反馈总结生成
description: 根据核查结果和上传材料，生成反馈总结

tools:
  - get_task_detail
  - parse_pdf
  - parse_word

prompts:
  main: |
    你是一个报告生成专家。
    
    请根据以下信息生成反馈总结：
    
    任务信息：{task_info}
    上传的材料：{uploaded_files}
    用户反馈内容：{user_feedback}
    
    请生成：
    1. 核查结果概述
    2. 发现的问题（如有）
    3. 建议措施
    4. 后续跟进建议
```

---

## 五、Agent层重构

### 5.1 统一入口设计

```python
class ManagerAgent:
    """主智能体 - 重构后"""
    
    def __init__(self, user_id: str, user_name: str):
        self.user_id = user_id
        self.user_name = user_name
        self.client = None
        self.tools = self._load_tools()      # 加载原子工具
        self.skills = self._load_skills()   # 加载Skill
        self._register_all()
    
    def _load_tools(self) -> Dict:
        """加载所有工具"""
        from .tools import file_parser, data_access, task_manager, file_ops
        return {
            "parse_csv": file_parser.parse_csv,
            "parse_excel": file_parser.parse_excel,
            "parse_pdf": file_parser.parse_pdf,
            "parse_word": file_parser.parse_word,
            "read_risk_data": data_access.read_r "list_users":isk_data,
            data_access.list_users,
            "get_task": data_access.get_task,
            "get_task_detail": data_access.get_task_detail,
            "create_task": task_manager.create_task,
            "update_task_status": task_manager.update_task_status,
            "query_tasks": task_manager.query_tasks,
            "save_uploaded_file": file_ops.save_uploaded_file,
        }
    
    def _load_skills(self) -> Dict:
        """加载所有Skill"""
        from .skills.skill_registry import get_all_skills
        return get_all_skills()
    
    def _register_all(self):
        """注册所有能力和Skill给SDK"""
        # 构建system prompt
        self.system_prompt = self._build_system_prompt()
        # 配置SDK选项
        self.options = self._build_options()
    
    def _build_system_prompt(self) -> str:
        """构建System Prompt"""
        return f"""你是一个风控智能助手。

你可以使用以下工具：{', '.join(self.tools.keys())}

你可以使用以下Skill：
{chr(10).join([f"- {name}: {skill.description}" for name, skill in self.skills.items()])}

用户会用自然语言表达他们的需求，你自己判断需要做什么，然后自主调用合适的工具或Skill来完成。

不要问用户"需要我帮你做这个吗"，直接理解意图并执行。
如果需要用户确认的信息（比如执行人人选），先给出建议再确认。
"""
    
    async def chat(self, message: str, context: Dict = None) -> str:
        """
        统一入口 - SDK自主处理
        
        用户说什么都可以，SDK自己判断：
        - 需要分析数据吗？
        - 需要推荐执行人吗？
        - 需要创建任务吗？
        - 需要查询状态吗？
        
        然后自主调用工具/Skill完成
        """
        # 构建prompt
        prompt = self._build_prompt(message, context)
        
        # 发送SDK处理
        await self.client.query(prompt)
        
        # 收集回复
        responses = []
        async for msg in self.client.receive_response():
            # 处理各种消息类型
            ...
        
        return "\n".join(responses)
```

### 5.2 SDK配置

```python
def _build_options(self) -> ClaudeAgentOptions:
    """构建SDK配置"""
    return ClaudeAgentOptions(
        env={...},
        system_prompt=self.system_prompt,
        permission_mode="acceptEdits",
        max_turns=20,  # 增加轮次，支持多步骤
        thinking={"type": "enabled"},  # 启用思考
        # 注册工具 + Skill
        tools=list(self.tools.keys()) + list(self.skills.keys()),
    )
```

---

## 六、开发计划

### 6.1 阶段一：工具层重构（第1-2天）

**目标**：将现有tools.py拆分为独立的原子工具模块

**任务**：
```
Day 1:
├── 创建 backend/agents/tools/ 目录
├── 实现 file_parser.py（从现有tools.py迁移）
├── 实现 data_access.py（从现有tools.py迁移）
└── 编写单元测试

Day 2:
├── 实现 task_manager.py
├── 实现 file_ops.py
├── 创建 tools/__init__.py 统一导出
└── 编写单元测试
```

**验收标准**：
- 所有原子工具可独立调用
- 原有功能保持不变
- 单元测试覆盖率 > 80%

---

### 6.2 阶段二：Skill层开发（第3-5天）

**目标**：封装业务场景为Skill

**任务**：
```
Day 3:
├── 创建 skills/ 目录结构
├── 实现 Skill 基类（skill_base.py）
├── 实现 SkillRegistry（skill_registry.py）
└── 定义 SKILL.md 规范

Day 4:
├── 实现 risk_analyzer Skill
├── 实现 receiver_recommender Skill
└── 实现 task_creator Skill

Day 5:
├── 实现核查_guider Skill
├── 实现 summary_generator Skill
└── 集成测试
```

**验收标准**：
- 每个Skill可独立执行
- SDK可识别并调用Skill
- 业务流程完整

---

### 6.3 阶段三：Agent重构（第6-7天）

**目标**：重构ManagerAgent和StaffAgent

**任务**：
```
Day 6:
├── 重构 ManagerAgent
│   ├── 统一chat()入口
│   ├── 自动注册工具+Skill
│   ├── 动态路由能力
└── 重构 StaffAgent（类似结构）

Day 7:
├── 前后端联调
├── 回归测试
└── 问题修复
```

**验收标准**：
- 对话完全灵活，支持任意表达
- SDK自主选择工具/Skill
- 原有功能100%兼容

---

### 6.4 阶段四：测试与优化（第8-10天）

**任务**：
```
Day 8:
├── 完整业务流程测试
├── 异常场景测试
└── 性能测试

Day 9:
├── 优化System Prompt
├── 优化工具/Skill描述
└── 边界情况处理

Day 10:
├── 文档更新
├── 代码Review
└── 合并到主分支
```

---

### 6.5 里程碑

| 阶段 | 里程碑 | 预计时间 |
|------|--------|----------|
| 阶段一 | 工具层完成 | Day 2 |
| 阶段二 | Skill层完成 | Day 5 |
| 阶段三 | Agent重构完成 | Day 7 |
| 阶段四 | 测试通过 | Day 10 |
| **总计** | **上线** | **10天** |

---

## 七、PRD变更建议

### 7.1 需要更新的内容

| 章节 | 当前内容 | 建议变更 |
|------|----------|----------|
| **三、功能需求** | 按固定环节描述 | 增加"灵活对话"能力描述 |
| **三、3.1.4 AI智能体对话** | 显式列举工具 | 描述为"自主理解意图并调用Skill/工具" |
| **六、Agent设计** | 固定方法设计 | 更新为"Skill+工具混合架构" |
| **九、成功指标** | 原有指标 | 增加意图识别准确率、Skill调用成功率等 |

### 7.2 新增需求建议

```markdown
### 3.1.7 灵活对话能力

- **意图理解**：AI能理解用户的自然语言表达
- **自主调用**：根据意图自主选择工具或Skill
- **多意图处理**：一句线话包含多个需求时依次处理
- **上下文记忆**：记住对话上下文，支持追问

**示例**：
- 用户："分析这批数据" → 自动分析
- 用户："那个任务让张三去查一下" → 自动创建任务
- 用户："之前那个风险数据有问题吗？" → 自动查询并回答
```

---

## 八、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| SDK自主调用不可控 | 可能调用错误工具 | 限制工具权限、输出边界 |
| 意图识别不准 | 用户意图被误解 | 增加确认环节 |
| 多意图处理乱序 | 同时要分析+创建 | 串行处理，关键节点确认 |
| 性能下降 | 多次API调用 | 缓存、合并请求 |

---

## 九、总结

本次架构升级核心：

1. **工具层**：原子化、通用化、可复用
2. **Skill层**：业务化、场景化、封装化
3. **Agent层**：统一入口、SDK自主路由

升级后：
- 用户可以任意表达需求
- SDK自主理解并调用合适的能力
- 新增业务只需添加Skill，无需改核心代码

---

**文档状态**: 待审核  
**下一步**: 根据审核意见调整设计文档
