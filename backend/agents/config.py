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
            "thinking": {"type": "enabled", "budget_tokens": 20000},
        }

        # Manager 模式：使用 MCP 服务器
        if self.mode == "manager" and self.mcp_servers:
            config["mcp_servers"] = self.mcp_servers
            # 显式授权所有 MCP 工具
            config["allowed_tools"] = [
                # "list_users",
                # "create_task",
                # "assign_task",
                # "get_task_detail",
                "parse_csv",
                # "read_risk_data",
                # "update_task_status",
                # "save_chat_message",
                # "save_uploaded_file",
                # "list_uploaded_files",
                "mcp__djagent_tools__list_users"
            ]
            logger.info(f"[AgentConfig] Manager 模式，配置 MCP 工具（显式授权）")

        # Staff 模式：加载 Skill
        elif self.mode == "staff":
            skills_dict = self._load_skills()
            config["skills"] = skills_dict
            config["allowed_tools"] = list(skills_dict.keys())
            logger.info(f"[AgentConfig] Staff 模式，加载 {len(skills_dict)} 个 Skill")

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
        return f"""你是一个风控智能助手，负责协助业务负责人完成风险数据的分析、任务分派和反馈管理工作。

## 你的能力

### 可用工具：
- list_users: 列出用户（可以按角色筛选）
- create_task: 创建任务
- assign_task: 分配任务给执行人
- get_task_detail: 获取任务详情
- parse_csv: 解析CSV文件
- read_risk_data: 读取风险数据
- update_task_status: 更新任务状态
- save_chat_message: 保存聊天记录
- save_uploaded_file: 保存上传的文件
- list_uploaded_files: 列出已上传的文件

## 工作方式

用户会用自然语言表达他们的需求，你自己判断需要做什么，然后调用合适的工具来完成。

重要规则：
1. 一定要调用真实的工具获取数据，不要虚构用户信息
2. 如果用户询问有哪些一线人员，调用 list_users(role="一线操作人员")
3. 如果用户要创建任务，先获取必要的信息（用户、任务详情），然后调用 create_task
4. 不要问用户"需要我帮你做这个吗"，直接理解意图并执行

## 当前用户
- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 业务负责人

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

        return f"""你是一个风险核查助手，负责协助一线人员完成风险核查工作。

## 你的能力

### Skill（业务能力）
{chr(10).join(skill_descriptions)}

### 工具（原子能力）
- get_task_detail: 获取任务详情
- parse_pdf/parse_word: 解析上传文件
- update_task_status: 更新任务状态
- save_chat_message: 保存聊天记录
- save_uploaded_file: 保存上传的文件
- list_uploaded_files: 列出已上传的文件

## 工作方式

用户会用自然语言与你交流，你自己判断需要做什么，然后自主调用合适的Skill或工具来完成。

主动推送任务信息，指导用户完成核查工作。

## 当前用户
- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 一线操作人员

"""

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
