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


def load_identity_document(mode: str) -> str:
    """
    从身份文档加载系统提示词

    Args:
        mode: "manager" 或 "staff"

    Returns:
        系统提示词内容 (如果加载失败则返回空字符串)
    """
    # 获取当前文件目录
    current_dir = Path(__file__).parent
    identity_dir = current_dir / "identity"

    if mode == "manager":
        doc_path = identity_dir / "MANAGER_AGENT.md"
    elif mode == "staff":
        doc_path = identity_dir / "STAFF_AGENT.md"
    else:
        logger.warning(f"[AgentConfig] Unknown mode: {mode}")
        return ""

    # 检查文件是否存在
    if not doc_path.exists():
        logger.error(
            f"[AgentConfig] Identity document NOT FOUND: {doc_path.absolute()}"
        )
        return ""

    try:
        # 读取文件
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证内容是否为空
        if not content or len(content.strip()) == 0:
            logger.error(
                f"[AgentConfig] Identity document is EMPTY: {doc_path.absolute()}"
            )
            return ""

        logger.info(
            f"[AgentConfig] Successfully loaded identity document: {doc_path.name} "
            f"({len(content)} bytes)"
        )
        return content

    except IOError as e:
        logger.error(
            f"[AgentConfig] Failed to read identity document: {doc_path.absolute()} "
            f"- {type(e).__name__}: {e}"
        )
        return ""
    except Exception as e:
        logger.error(
            f"[AgentConfig] Unexpected error loading identity document: {doc_path.absolute()} "
            f"- {type(e).__name__}: {e}"
        )
        return ""


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
                "mcp__djagent_tools__get_current_time",
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
                # Data query tools
                "mcp__djagent_tools__list_tables",
                "mcp__djagent_tools__describe_table",
                "mcp__djagent_tools__query_data",
                "mcp__djagent_tools__query_risk_data",
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
        # 从身份文档加载系统提示词
        identity_content = load_identity_document(self.mode)

        if not identity_content:
            # 文件加载失败，抛出错误
            error_msg = (
                f"[AgentConfig] Critical Error: Identity document not found for mode '{self.mode}'. "
                f"Required file: backend/agents/identity/{self.mode.upper()}_AGENT.md"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # 添加用户信息到提示词末尾
        user_info = f"\n\n## 当前用户\n- 用户ID: {self.user_id}\n- 用户名: {self.user_name}\n- 角色: {'业务负责人' if self.mode == 'manager' else '一线操作人员'}\n"
        logger.info(f"[AgentConfig] Successfully loaded system prompt for mode '{self.mode}' with user info appended")

        return identity_content + user_info


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
                ("create_task", "创建任务，参数：task_info（包含creator_id, creator_name, assigned_to_id, assigned_to_name, risk_summary, task_type（可选，'日度'或'月度'，默认'日度'））"),
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

        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent

        options = {
            "env": self.env_config,
            "system_prompt": self.system_prompt,
            "max_turns": self.max_turns,
            "cwd": str(project_root),                    # 设置项目根目录
            "setting_sources": ["user", "project"],      # 启用官方 Skill 发现
            "include_partial_messages": True,            # 🔥 关键：开启流式输出
            **self.tools_config,
        }

        # 在 allowed_tools 中添加 Skill 支持
        if "allowed_tools" not in options:
            options["allowed_tools"] = []

        if isinstance(options["allowed_tools"], list):
            options["allowed_tools"].append("Skill")
            logger.info(f"[AgentConfig] 启用官方 Skill 支持，允许的工具: {options['allowed_tools']}")

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
    mcp_servers: Optional[Dict[str, Any]] = None,
    skills: Optional[List[str]] = None,
    **kwargs,
) -> AgentConfig:
    """
    创建 Staff 配置

    Args:
        user_id: 用户ID
        user_name: 用户名称
        mcp_servers: MCP 服务器配置
        skills: 要加载的 Skill 列表
        **kwargs: 其他配置参数

    Returns:
        AgentConfig 实例
    """
    return AgentConfig(
        user_id=user_id, user_name=user_name, mode="staff", mcp_servers=mcp_servers, skills=skills, **kwargs
    )
