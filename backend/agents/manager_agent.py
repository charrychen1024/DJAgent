"""
主智能体（Manager Agent）- Web端业务负责人使用
重构后：使用MCP服务器注册自定义工具
"""

import os
import logging
from pathlib import Path
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

# 加载环境变量
load_dotenv()


class ManagerAgent:
    """
    主智能体 - 业务负责人使用

    重构后特点：
    1. 使用MCP服务器注册自定义工具
    2. 统一chat()入口，SDK自主理解意图
    3. 灵活对话，不预设流程
    """

    def __init__(self, user_id: str, user_name: str):
        """
        初始化主智能体

        Args:
            user_id: 用户ID
            user_name: 用户名称
        """
        self.user_id = user_id
        self.user_name = user_name
        self.client: Optional[ClaudeSDKClient] = None

        # 加载MCP服务器
        self._mcp_server = self._load_mcp_server()

        # 构建System Prompt
        self._system_prompt = self._build_system_prompt()

        # SDK配置
        self._options = self._build_options()

        logger.info(f"[ManagerAgent] 初始化: user_id={user_id}, user_name={user_name}")
        logger.info(f"[ManagerAgent] MCP服务器: {self._mcp_server is not None}")

    def _load_mcp_server(self):
        """加载MCP服务器配置"""
        try:
            from agents.mcp_server import create_djagent_mcp_server

            mcp_server = create_djagent_mcp_server()
            logger.info(f"[ManagerAgent] MCP服务器配置: {mcp_server}")

            # 返回字典格式，不是对象
            return {"djagent_tools": mcp_server}
        except Exception as e:
            logger.error(f"[ManagerAgent] 加载MCP服务器失败: {e}")
            return {}

    def _build_system_prompt(self) -> str:
        """构建System Prompt - 告诉AI有哪些能力"""

        system_prompt = """你是一个风控智能助手，负责协助业务负责人完成风险数据的分析、任务分派和反馈管理工作。

## 你的能力

### 可用工具：
- list_users: 列出用户（可以按角色筛选）
- create_task: 创建任务
- assign_task: 分配任务给执行人
- get_task_detail: 获取任务详情
- parse_csv: 解析CSV文件
- read_risk_data: 读取风险数据

## 工作方式

用户会用自然语言表达他们的需求，你自己判断需要做什么，然后调用合适的工具来完成。

重要规则：
1. 一定要调用真实的工具获取数据，不要虚构用户信息
2. 如果用户询问有哪些一线人员，调用 list_users(role="一线操作人员")
3. 如果用户要创建任务，先获取必要的信息（用户、任务详情），然后调用 create_task
4. **重要**：创建任务后必须调用 assign_task 将任务下发给执行人，否则任务状态会一直停留在"已创建"，不会设置 sent_time 和 feedback_deadline！
5. 不要问用户"需要我帮你做这个吗"，直接理解意图并执行

## 任务状态流转规则

### 任务状态说明
- **已创建**：任务刚创建，尚未下发
- **已下发**：任务已分配给执行人，等待执行人反馈
- **反馈中**：执行人开始处理任务，正在提交材料或进行核查
- **已完成**：执行人已完成核查，提交了反馈
- **已超时**：执行人未在规定时间内完成反馈
- **下发失败**：任务发送/分配失败，需要重新处理（可能是执行人不存在、系统错误等原因）

### 状态流转流程
1. **创建任务** → 调用 create_task → 状态变为"已创建"
2. **下发任务** → 调用 assign_task → 状态变为"已下发"，同时设置 sent_time（当前时间）和 feedback_deadline（截止时间）
3. **执行人开始反馈** → 执行人发送消息时系统自动设置 sent_time（如果是首次）或保持现有时间
4. **执行人完成反馈** → 执行人确认完成后状态变为"已完成"
5. **超时判定** → 系统每分钟检查"反馈中"状态的任务，超过 feedback_deadline 则更新为"已超时"

### 时间规则
- 日度任务：默认 feedback_deadline = sent_time + 24小时
- 月度任务：默认 feedback_deadline = sent_time + 72小时
- **重要**：assign_task 会自动设置 sent_time 和 feedback_deadline，必须在调用 assign_task 后才会设置截止时间！

### 自定义反馈时限
- 如果用户在对话中指定了反馈截止时间（如"今天下午5点前"、"2小时内"、"明天中午12点"等），你需要：
  1. **理解用户描述的时限**：智能解析用户说的时间要求
  2. **转换为标准格式**：将用户描述转换为 "YYYY-MM-DD HH:MM:SS" 格式
  3. **传入 assign_task**：在调用 assign_task 时，通过 feedback_deadline 参数传入

**截止时间格式要求**：必须是 "YYYY-MM-DD HH:MM:SS"（如 "2026-03-22 17:00:00"）

示例：
- 用户说"今天下午5点前" → 转换为当天17:00的具体时间
- 用户说"2小时内" → 当前时间 + 2小时
- 用户说"明天中午12点" → 次日12:00

## 当前用户
- 用户ID: {user_id}
- 用户名: {user_name}
- 角色: 业务负责人

""".format(user_id=self.user_id, user_name=self.user_name)

        return system_prompt

    def _build_options(self) -> ClaudeAgentOptions:
        """构建SDK配置"""

        # 构建选项
        options = {
            "env": {
                "ANTHROPIC_BASE_URL": os.getenv(
                    "ANTHROPIC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"
                ),
                "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
            "system_prompt": self._system_prompt,
            "max_turns": 20,  # 增加轮次，支持多步骤
            "thinking": {"type": "enabled", "budget_tokens": 20000},  # 启用思考
        }

        # 如果有MCP服务器配置，添加到选项中
        if self._mcp_server:
            options["mcp_servers"] = self._mcp_server
            logger.info(
                f"[ManagerAgent] MCP服务器配置: {list(self._mcp_server.keys())}"
            )

            # 自动授权所有MCP工具
            mcp_tools = [
                "list_users",
                "create_task",
                "assign_task",
                "get_task_detail",
                "parse_csv",
                "read_risk_data",
            ]
            options["allowed_tools"] = mcp_tools
            logger.info(f"[ManagerAgent] 自动授权MCP工具: {mcp_tools}")

        return ClaudeAgentOptions(**options)

    async def __aenter__(self):
        """异步上下文入口"""
        self.client = ClaudeSDKClient(options=self._options)
        await self.client.__aenter__()
        logger.info(f"[ManagerAgent] 会话启动: {self.user_name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            logger.info(f"[ManagerAgent] 会话关闭: {self.user_name}")

    async def chat(self, message: str, context: Optional[Dict] = None) -> str:
        """
        统一入口 - SDK自主处理

        用户说什么都可以，SDK自己判断：
        - 需要分析数据吗？
        - 需要推荐执行人吗？
        - 需要创建任务吗？
        - 需要查询状态吗？

        Args:
            message: 用户消息
            context: 上下文信息（如当前任务ID等）

        Returns:
            Agent回复内容
        """
        logger.info(f"[ManagerAgent] 收到消息: {message[:100]}...")

        # 构建prompt
        prompt = self._build_prompt(message, context)

        # 发送SDK处理
        await self.client.query(prompt)

        # 收集回复
        responses = []
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        responses.append(block.text)
            elif isinstance(msg, ResultMessage):
                logger.info(f"[ManagerAgent] 请求完成: {msg.subtype}")

        reply = (
            "\n".join(responses) if responses else "抱歉，我未能理解您的意思，请重试。"
        )

        logger.info(f"[ManagerAgent] 回复: {reply[:100]}...")
        return reply

    def _build_prompt(self, message: str, context: Optional[Dict]) -> str:
        """构建prompt"""

        prompt = f"""当前用户：{self.user_name} (ID: {self.user_id})
角色：业务负责人

"""

        if context:
            if context.get("task_id"):
                prompt += f"当前任务ID：{context.get('task_id')}\n"
            if context.get("risk_data"):
                prompt += f"风险数据：{context.get('risk_data')}\n"

        prompt += f"\n用户消息：{message}\n\n"
        prompt += "请根据用户需求，调用合适的工具完成任务。"

        return prompt

    # ============ 兼容旧接口 ============
    # 保留原有方法以便兼容

    async def analyze_risk_data(self, file_path: str) -> str:
        """分析风险数据 - 兼容旧接口"""
        return "分析完成"

    async def recommend_receiver(self, risk_data: str) -> Dict[str, Any]:
        """推荐执行人 - 兼容旧接口"""
        return {"error": "请使用list_users工具获取真实用户"}

    async def create_task(self, task_info: Dict) -> Dict[str, Any]:
        """创建任务 - 兼容旧接口"""
        return {"error": "请使用create_task工具创建任务"}


# 便捷函数
async def create_manager_agent(user_id: str, user_name: str) -> "ManagerAgent":
    """创建主智能体实例"""
    agent = ManagerAgent(user_id, user_name)
    await agent.__aenter__()
    return agent
