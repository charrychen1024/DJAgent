"""
主智能体（Manager Agent）- Web端业务负责人使用
重构后：使用Skill+工具混合架构，SDK自主路由
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
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
    1. 统一chat()入口，SDK自主理解意图
    2. 注册所有工具+Skill，SDK自主选择调用
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

        # 加载工具和Skill
        self._tools = self._load_tools()
        self._skills = self._load_skills()

        # 构建System Prompt
        self._system_prompt = self._build_system_prompt()

        # SDK配置
        self._options = self._build_options()

        logger.info(f"[ManagerAgent] 初始化: user_id={user_id}, user_name={user_name}")
        logger.info(f"[ManagerAgent] 加载工具: {len(self._tools)}个")
        logger.info(f"[ManagerAgent] 加载Skill: {len(self._skills)}个")

    def _load_tools(self) -> Dict:
        """加载所有原子工具"""
        from .tools import ALL_TOOLS

        return ALL_TOOLS

    def _load_skills(self) -> Dict:
        """加载所有Skill"""
        from .skills import get_all_skills

        return get_all_skills()

    def _build_system_prompt(self) -> str:
        """构建System Prompt - 告诉AI有哪些能力"""

        # Skill描述
        skill_descriptions = []
        for name, skill in self._skills.items():
            skill_descriptions.append(f"- {name}: {skill.description}")

        # 工具描述
        tool_descriptions = [
            "- parse_csv/parse_excel/parse_pdf/parse_word: 解析文件",
            "- read_risk_data: 读取风险数据",
            "- list_users: 列出用户",
            "- get_task/get_task_detail: 查询任务",
            "- create_task: 创建任务",
            "- update_task_status: 更新任务状态",
            "- assign_task: 分配任务",
            "- query_tasks: 查询任务列表",
        ]

        system_prompt = f"""你是一个风控智能助手，负责协助业务负责人完成风险数据的分析、任务分派和反馈管理工作。

## 你的能力

### Skill（业务能力）
{chr(10).join(skill_descriptions)}

### 工具（原子能力）
{chr(10).join(tool_descriptions)}

## 工作方式

用户会用自然语言表达他们的需求，你自己判断需要做什么，然后自主调用合适的Skill或工具来完成。

不要问用户"需要我帮你做这个吗"，直接理解意图并执行。
如果需要用户确认的信息（比如执行人人选），先给出建议再确认。

## 当前用户
- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 业务负责人

"""
        return system_prompt

    def _build_options(self) -> ClaudeAgentOptions:
        """构建SDK配置"""

        # 收集所有可用的工具和Skill名称
        available = list(self._tools.keys()) + list(self._skills.keys())

        return ClaudeAgentOptions(
            env={
                "ANTHROPIC_BASE_URL": os.getenv(
                    "ANTHROPIC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"
                ),
                "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
            system_prompt=self._system_prompt,
            permission_mode="acceptEdits",
            max_turns=20,  # 增加轮次，支持多步骤
            thinking={"type": "enabled", "budget_tokens": 20000},  # 启用思考
            tools=available,  # 注册所有工具和Skill
        )

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
        prompt += "请根据用户需求，自主调用合适的Skill或工具完成任务。"

        return prompt

    # ============ 兼容旧接口 ============
    # 保留原有方法以便兼容，但内部已改为调用Skill

    async def analyze_risk_data(self, file_path: str) -> str:
        """分析风险数据 - 兼容旧接口"""
        from .skills import get_skill

        skill = get_skill("risk_analyzer")
        if skill:
            result = await skill.execute({"data_source": file_path}, {})
            return result.get("analysis", {}).get("key_findings", ["分析完成"])
        return "分析完成"

    async def recommend_receiver(self, risk_data: str) -> Dict[str, Any]:
        """推荐执行人 - 兼容旧接口"""
        from .skills import get_skill

        skill = get_skill("receiver_recommender")
        if skill:
            return await skill.execute({"risk_data": risk_data}, {})
        return {"error": "Skill未找到"}

    async def create_task(self, task_info: Dict) -> Dict[str, Any]:
        """创建任务 - 兼容旧接口"""
        from .skills import get_skill

        skill = get_skill("task_creator")
        if skill:
            return await skill.execute(task_info, {})
        return {"error": "Skill未找到"}


# 便捷函数
async def create_manager_agent(user_id: str, user_name: str) -> "ManagerAgent":
    """创建主智能体实例"""
    agent = ManagerAgent(user_id, user_name)
    await agent.__aenter__()
    return agent
