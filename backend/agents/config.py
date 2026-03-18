"""
Agent 配置类 - 统一的 Agent 配置管理
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


class AgentConfig:
    """
    统一的 Agent 配置类

    功能：
    1. 支持 Manager 和 Staff 两种模式
    2. 动态配置 Skill 集合
    3. 自定义 System Prompt
    4. MCP 服务器配置
    """

    def __init__(
        self,
        user_id: str,
        user_name: str,
        mode: str = "manager",
        custom_system_prompt: Optional[str] = None,
        mcp_servers: Optional[Dict[str, Any]] = None,
        skills: Optional[List[str]] = None,
        max_turns: int = 20,
    ):
        """
        初始化 Agent 配置

        Args:
            user_id: 用户ID
            user_name: 用户名称
            mode: Agent 模式 - "manager" 或 "staff"
            custom_system_prompt: 自定义 System Prompt
            mcp_servers: MCP 服务器配置
            skills: 要加载的 Skill 列表（None 表示加载全部）
            max_turns: 最大对话轮次
        """
        self.user_id = user_id
        self.user_name = user_name
        self.mode = mode
        self.mcp_servers = mcp_servers or {}
        self.skills = skills
        self.max_turns = max_turns

        # 构建配置
        self.system_prompt = custom_system_prompt or self._build_default_system_prompt()
        self.env_config = self._build_env_config()
        self.tools_config = self._build_tools_config()

        logger.info(
            f"[AgentConfig] 初始化: mode={mode}, user={user_name}, skills={len(skills) if skills else 'all'}"
        )

    def _build_env_config(self) -> Dict[str, str]:
        """构建环境配置"""
        return {
            "ANTHROPIC_BASE_URL": os.getenv(
                "ANTHROPIC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"
            ),
            "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        }

    def _build_tools_config(self) -> Dict[str, Any]:
        """构建工具配置"""
        config = {
            "thinking": {"type": "disabled", "budget_tokens": 20000},
        }

        # Manager 模式：使用 MCP 服务器
        if self.mode == "manager" and self.mcp_servers:
            config["mcp_servers"] = self.mcp_servers
            # 显式授权所有 MCP 工具（使用 mcp__ 命名空间）
            config["allowed_tools"] = [
                "mcp__djagent_tools__list_users",
                "mcp__djagent_tools__create_task",
                "mcp__djagent_tools__assign_task",
                "mcp__djagent_tools__get_task_detail",
                "mcp__djagent_tools__parse_csv",
                "mcp__djagent_tools__parse_excel",
                "mcp__djagent_tools__parse_pdf",
                "mcp__djagent_tools__parse_word",
                "mcp__djagent_tools__read_risk_data",
                "mcp__djagent_tools__update_task_status",
                "mcp__djagent_tools__save_chat_message",
                "mcp__djagent_tools__save_uploaded_file",
                "mcp__djagent_tools__list_uploaded_files",
            ]
            logger.info(f"[AgentConfig] Manager 模式，配置 {len(config['allowed_tools'])} 个 MCP 工具（显式授权）")

        # Staff 模式：使用 MCP 工具
        elif self.mode == "staff":
            # Staff 模式下配置 MCP 工具
            if self.mcp_servers:
                config["mcp_servers"] = self.mcp_servers
                # Staff 需要的基础 MCP 工具
                staff_mcp_tools = [
                    "mcp__djagent_tools__get_task_detail",
                    "mcp__djagent_tools__parse_csv",
                    "mcp__djagent_tools__update_task_status",
                    "mcp__djagent_tools__save_chat_message",
                    "mcp__djagent_tools__save_uploaded_file",
                    "mcp__djagent_tools__list_uploaded_files",
                ]
                config["allowed_tools"] = staff_mcp_tools
                logger.info(f"[AgentConfig] Staff 模式，配置 {len(staff_mcp_tools)} 个 MCP 工具")
            else:
                config["allowed_tools"] = []
                logger.info(f"[AgentConfig] Staff 模式，未配置 MCP 工具")

        return config

    def _load_skills(self) -> Dict[str, Any]:
        """加载 Skill"""
        from .skills import get_all_skills

        all_skills = get_all_skills()

        if self.skills is None:
            return all_skills
        else:
            return {
                name: skill for name, skill in all_skills.items() if name in self.skills
            }

    def _build_default_system_prompt(self) -> str:
        """构建默认 System Prompt"""
        if self.mode == "manager":
            return self._build_manager_prompt()
        elif self.mode == "staff":
            return self._build_staff_prompt()
        else:
            return ""

    def _build_manager_prompt(self) -> str:
        """构建 Manager 模式 System Prompt"""
        # 动态获取工具描述
        tools_desc = self._get_tools_description()

        return f"""你是「DJAgent风控智能助手」，一个专注于物流快递领域风险管理的AI协控助手。

## 身份定义

你由Charry团队构建，专注于帮助业务负责人完成风险数据分析、任务分派和反馈管理。

## 知识边界

- 你的风控知识截止到2025年12月
- 你可以调用工具查询系统中的实时数据（任务、用户、文件、风险数据等）
- 对于实时行业信息，使用搜索工具获取最新数据

## 核心能力

### 可用工具：
{tools_desc}

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

    def _build_staff_prompt(self) -> str:
        """构建 Staff 模式 System Prompt"""
        skill_descriptions = []
        if self.skills is None:
            from .skills import get_all_skills

            all_skills = get_all_skills()
            for name, skill in all_skills.items():
                skill_descriptions.append(f"- {name}: {skill.description}")
        else:
            for skill_name in self.skills:
                from .skills import get_skill

                skill = get_skill(skill_name)
                if skill:
                    skill_descriptions.append(f"- {skill_name}: {skill.description}")

        # 动态获取工具描述
        tools_desc = self._get_tools_description(staff_mode=True)

        return f"""你是「DJAgent风险核查助手」，一个专注于物流快递一线核查工作的AI协控助手。

## 身份定义

你由Charry团队构建，专注于帮助一线操作人员完成风险核查任务。

## 知识边界

- 你的风控知识截止到2025年12月
- 你可以调用工具查询任务详情、解析文件、提交核查结果

## 能力体系

### Skills（业务能力）
{chr(10).join(skill_descriptions) if skill_descriptions else "（暂无配置）"}

### 工具（原子能力）
{tools_desc}

## 工作流程

1. **接收任务**：从任务描述中提取核查要点
2. **分析数据**：调用解析工具查看相关数据
3. **判断风险**：根据数据判断是否存在风险
4. **反馈结果**：调用update_task_status提交核查结果

## 输出格式

### 任务确认
**任务ID**：[任务ID]
**风险类型**：[类型]
**核查要点**：[需要确认的1-2-3点]

### 核查结果
**核查结论**：[存在风险/无风险/无法确认]
**具体说明**：
1. [发现的问题]
2. [数据支撑]
**下一步建议**：[继续处理/转派他人/结束任务]

## 行为准则

1. **主动指导**：不等用户问，主动推送任务状态和下一步操作
2. **数据驱动**：用数据说话，引用具体的运单号、时间、数量
3. **操作闭环**：每次交互都要推动任务向前，不能只是"好的，我了解了"
4. **边界意识**：超出权限的操作（如删除数据），明确告知需要上级审批

## 当前用户
- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 一线操作人员

---

**重要**：你是通过工具来完成核查任务，而不是在回复中描述会做什么。当需要执行操作时，直接调用合适的工具。

"""

    def _get_tools_description(self, staff_mode: bool = False) -> str:
        """动态获取工具描述"""
        if staff_mode:
            # Staff 模式的工具列表
            tools = [
                ("get_task_detail", "获取任务详情，参数：task_id"),
                ("parse_csv", "解析CSV文件，参数：file_path"),
                ("parse_excel", "解析Excel文件，参数：file_path, sheet_name"),
                ("parse_pdf", "解析PDF文件，参数：file_path, max_pages"),
                ("parse_word", "解析Word文档，参数：file_path"),
                ("update_task_status", "更新任务状态，参数：task_id, status"),
                ("save_chat_message", "保存聊天记录，参数：task_id, user_id, user_name, message"),
                ("save_uploaded_file", "保存上传文件，参数：task_id, file_path, file_name"),
                ("list_uploaded_files", "列出已上传文件，参数：task_id"),
            ]
        else:
            # Manager 模式的工具列表
            tools = [
                ("list_users", "列出用户，参数：role（可选，按角色筛选）"),
                ("create_task", "创建任务，参数：task_info（包含creator_id, creator_name, assigned_to_id, assigned_to_name, risk_summary）"),
                ("assign_task", "分配任务，参数：task_id, assigned_to_id, assigned_to_name, status"),
                ("get_task_detail", "获取任务详情，参数：task_id"),
                ("parse_csv", "解析CSV文件，参数：file_path"),
                ("parse_excel", "解析Excel文件，参数：file_path, sheet_name"),
                ("parse_pdf", "解析PDF文件，参数：file_path, max_pages"),
                ("parse_word", "解析Word文档，参数：file_path"),
                ("read_risk_data", "读取风险数据，参数：filename"),
                ("update_task_status", "更新任务状态，参数：task_id, status"),
                ("save_chat_message", "保存聊天记录，参数：task_id, user_id, user_name, message"),
                ("save_uploaded_file", "保存上传文件，参数：task_id, file_path, file_name"),
                ("list_uploaded_files", "列出已上传文件，参数：task_id"),
            ]

        lines = []
        for name, desc in tools:
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def to_sdk_options(self):
        """转换为 SDK 配置"""
        from claude_agent_sdk import ClaudeAgentOptions

        options = {
            "env": self.env_config,
            "system_prompt": self.system_prompt,
            "max_turns": self.max_turns,
            **self.tools_config,
        }

        return ClaudeAgentOptions(**options)


def create_manager_config(
    user_id: str,
    user_name: str,
    mcp_servers: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> AgentConfig:
    """
    创建 Manager 配置

    Args:
        user_id: 用户ID
        user_name: 用户名称
        mcp_servers: MCP 服务器配置
        **kwargs: 其他配置参数

    Returns:
        AgentConfig 实例
    """
    return AgentConfig(
        user_id=user_id,
        user_name=user_name,
        mode="manager",
        mcp_servers=mcp_servers,
        **kwargs,
    )


def create_staff_config(
    user_id: str,
    user_name: str,
    skills: Optional[List[str]] = None,
    **kwargs,
) -> AgentConfig:
    """
    创建 Staff 配置

    Args:
        user_id: 用户ID
        user_name: 用户名称
        skills: 要加载的 Skill 列表
        **kwargs: 其他配置参数

    Returns:
        AgentConfig 实例
    """
    return AgentConfig(
        user_id=user_id, user_name=user_name, mode="staff", skills=skills, **kwargs
    )
