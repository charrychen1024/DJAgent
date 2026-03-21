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
        系统提示词内容
    """
    # 获取当前文件目录
    current_dir = Path(__file__).parent
    identity_dir = current_dir / "identity"

    if mode == "manager":
        doc_path = identity_dir / "MANAGER_AGENT.md"
    elif mode == "staff":
        doc_path = identity_dir / "STAFF_AGENT.md"
    else:
        logger.warning(f"[AgentConfig] 未知模式: {mode}")
        return ""

    if not doc_path.exists():
        logger.error(f"[AgentConfig] 身份文档不存在: {doc_path}")
        return ""

    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"[AgentConfig] 已加载身份文档: {doc_path.name}")
        return content
    except Exception as e:
        logger.error(f"[AgentConfig] 读取身份文档失败: {e}")
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
        # 优先从身份文档加载
        identity_content = load_identity_document(self.mode)
        if identity_content:
            # 添加用户信息
            user_info = f"\n\n## 当前用户\n- 用户ID: {self.user_id}\n- 用户名: {self.user_name}\n- 角色: {'业务负责人' if self.mode == 'manager' else '一线操作人员'}\n"
            return identity_content + user_info
        
        # 如果文档加载失败，使用旧的硬编码方式
        if self.mode == "manager":
            return self._build_manager_prompt()
        elif self.mode == "staff":
            return self._build_staff_prompt()
        else:
            return ""

    def _build_manager_prompt(self) -> str:
        """构建 Manager 模式 System Prompt（备用方案）"""
        return f"""你是「DJAgent风控智能助手」，一个专注于物流快递领域风险管理的AI协控助手。

## 身份定义

你由DJAgent风控团队构建，专注于帮助业务负责人完成风险数据分析、任务分派和反馈管理。

## 核心能力

你可以调用工具完成数据查询、任务管理、文件解析等操作。具体使用哪些工具，由你根据用户需求自主判断。

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
5. **任务闭环**：创建任务后必须指定执行人，确保任务可以下发

## 当前用户
- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 业务负责人

---

**重要**：你是通过工具来完成任务，而不是在回复中描述会做什么。当需要执行操作时，直接调用合适的工具。

"""

    def _build_staff_prompt(self) -> str:
        """构建 Staff 模式 System Prompt"""
        return f"""你是「DJAgent风险核查助手」，由DJAgent风控团队构建，专注于帮助一线操作人员完成风险核查任务。

## 身份定义

你是一个风险核查助手，你的核心职责有**两个阶段**：

### 阶段一：任务下发（主动推送）

当Manager创建了风险核查任务并调用你时，你需要**主动发消息**给对应的一线用户，告知：
- 任务ID和风险类型
- 需要提交什么材料（图片/文档/文字）
- 需要反馈什么内容（业务真实性、操作情况等）

**重要**：你是告知用户需要提交什么材料，**不是教用户怎么核查**。

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

## 核心能力

你可以调用工具完成任务查询、文件解析、状态更新等操作。具体使用哪些工具，由你根据需求自主判断。

## 输出格式

### 任务通知消息
当收到新任务时，主动发送：
**任务编号**：[任务ID]
**风险类型**：[类型]
**需要提交的材料**：
1. [材料1]
2. [材料2]
**反馈截止时间**：[时间]

### 收到材料后的核查总结
**材料完整性**：✅ 完整 / ⚠️ 缺失 {{缺少什么}}
**风险分析结论**：
- 【真实风险】：{{风险真实存在，说明}}
- 【问题不大】：{{风险存在但轻微，说明}}
- 【无风险】：{{经核实无风险，说明}}

**下一步建议**：
- 【通过】：材料齐全，风险已核实
- 【补充】：材料不完整，需要补充 {{具体}}
- 【转派】：需要其他人员处理（原因）
- 【关闭】：风险不存在，任务关闭

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
