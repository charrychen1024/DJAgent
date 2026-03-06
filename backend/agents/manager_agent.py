"""
主智能体（Manager Agent）- Web端业务负责人使用
负责：分析风险数据、创建任务、下发任务给一线人员
"""

import os
import json
import csv
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)
from dotenv import load_dotenv
import asyncio

# 导入工具函数
from .tools import (
    parse_csv,
    parse_excel,
    parse_pdf,
    parse_word,
    read_risk_data,
    list_users,
    get_task_status,
    AGENT_TOOLS,
)

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent / "data"


# System Prompt - 主智能体
MANAGER_SYSTEM_PROMPT = """你是一个风险控制专家Agent，负责协助业务负责人完成风险数据的分析、任务分派和反馈管理工作。

你的核心职责：
1. 帮助业务负责人分析上传的风险数据，识别风险特征和关键信息
2. 基于风险数据推荐合适的一线人员进行核查
3. 协助业务负责人完成任务的创建和分派
4. 回答业务负责人关于风险分析方法、任务管理流程的问题
5. 提供风险分析报告和建议

你具备以下工具能力：
- parse_csv: 解析CSV文件
- parse_excel: 解析Excel文件
- parse_pdf: 解析PDF文档
- parse_word: 解析Word文档
- read_risk_data: 读取风险数据CSV文件
- list_users: 列出可用的执行人员
- get_task_status: 查询任务状态

工作流程：
1. 用户上传风险数据文件 → 你分析数据
2. 你推荐合适的执行人 → 用户确认
3. 用户确认创建任务 → 你创建并下发任务

请以专业、友好的语气与业务负责人对话，提供准确的分析和建议。
"""


def build_manager_options() -> ClaudeAgentOptions:
    """构建主智能体配置"""
    return ClaudeAgentOptions(
        env={
            "ANTHROPIC_BASE_URL": os.getenv(
                "ANTHROPIC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"
            ),
            "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        system_prompt=MANAGER_SYSTEM_PROMPT,
        permission_mode="acceptEdits",
        max_turns=15,
        thinking={"type": "disabled"},
        tools=[tool.__name__ for tool in AGENT_TOOLS],
    )


class ManagerAgent:
    """
    主智能体 - 业务负责人使用
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
        self.options = build_manager_options()
        logger.info(f"[ManagerAgent] 初始化: user_id={user_id}, user_name={user_name}")

    async def __aenter__(self):
        """异步上下文入口"""
        self.client = ClaudeSDKClient(options=self.options)
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
        发送消息并获取回复

        Args:
            message: 用户消息
            context: 上下文信息（如当前任务ID等）

        Returns:
            Agent回复内容
        """
        logger.info(f"[ManagerAgent] 收到消息: {message[:100]}...")

        # 构建prompt，包含上下文
        prompt = f"""当前用户：{self.user_name} (ID: {self.user_id})

"""

        if context:
            if context.get("task_id"):
                prompt += f"当前任务ID：{context.get('task_id')}\n"
            if context.get("risk_data"):
                prompt += f"风险数据：{context.get('risk_data')}\n"

        prompt += f"\n用户消息：{message}"

        logger.info(f"[ManagerAgent] 发送prompt给AI...")

        # 发送消息
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

    async def analyze_risk_data(self, file_path: str) -> str:
        """
        分析风险数据

        Args:
            file_path: 数据文件路径

        Returns:
            分析结果
        """
        logger.info(f"[ManagerAgent] 分析风险数据: {file_path}")

        # 使用工具解析文件
        if file_path.endswith(".csv"):
            result = parse_csv(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            result = parse_excel(file_path)
        elif file_path.endswith(".pdf"):
            result = parse_pdf(file_path)
        elif file_path.endswith((".docx", ".doc")):
            result = parse_word(file_path)
        else:
            return f"不支持的文件类型: {file_path}"

        if "error" in result:
            logger.error(f"[ManagerAgent] 解析失败: {result['error']}")
            return f"解析文件失败: {result['error']}"

        # 让AI分析数据
        analysis_prompt = f"""请分析以下风险数据：
        
{result.get("summary", "")}

数据预览：
{json.dumps(result.get("preview", []), ensure_ascii=False, indent=2)}

请识别：
1. 主要风险模式
2. 异常数据
3. 涉及的人员和部门
4. 风险等级评估
"""

        await self.client.query(analysis_prompt)

        responses = []
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        responses.append(block.text)

        reply = "\n".join(responses) if responses else "分析完成，但未生成有效结果。"
        logger.info(f"[ManagerAgent] 分析完成: {reply[:100]}...")
        return reply

    async def recommend_receiver(self, risk_data: str) -> Dict[str, Any]:
        """
        推荐执行人

        Args:
            risk_data: 风险数据摘要

        Returns:
            推荐结果
        """
        logger.info("[ManagerAgent] 推荐执行人")

        # 获取一线人员列表
        users_result = list_users(role="一线操作人员")

        if "error" in users_result:
            return {"error": "获取用户列表失败"}

        prompt = f"""根据以下风险数据，推荐最合适的执行人：

风险数据摘要：{risk_data}

可选执行人：
{json.dumps(users_result.get("users", []), ensure_ascii=False, indent=2)}

请推荐最合适的1-2个人选，并说明推荐理由。返回格式：
推荐人: [姓名]
推荐理由: [原因]
"""

        await self.client.query(prompt)

        responses = []
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        responses.append(block.text)

        reply = "\n".join(responses)
        logger.info(f"[ManagerAgent] 推荐结果: {reply[:100]}...")

        return {
            "success": True,
            "recommendation": reply,
            "available_users": users_result.get("users", []),
        }

    async def create_task(self, task_info: Dict) -> Dict[str, Any]:
        """
        创建任务

        Args:
            task_info: 任务信息

        Returns:
            创建结果
        """
        logger.info(f"[ManagerAgent] 创建任务: {task_info}")

        # 生成任务ID
        tasks_file = DATA_DIR / "tasks.csv"
        task_id = "TASK_001"

        if tasks_file.exists():
            with open(tasks_file, "r", encoding="utf-8") as f:
                existing = f.readlines()
                if len(existing) > 1:
                    last_id = existing[-1].split(",")[0]
                    num = int(last_id.split("_")[1]) + 1
                    task_id = f"TASK_{num:03d}"

        # 保存任务到CSV
        task_row = {
            "task_id": task_id,
            "creator_id": self.user_id,
            "creator_name": self.user_name,
            "assigned_to_id": task_info.get("assigned_to_id", ""),
            "assigned_to_name": task_info.get("assigned_to_name", ""),
            "status": "已创建",
            "created_time": task_info.get("created_time", ""),
            "risk_summary": task_info.get("risk_summary", ""),
            "risk_data_url": task_info.get("risk_data_url", ""),
            "suggested_receiver_id": task_info.get("suggested_receiver_id", ""),
            "confirmed_receiver_id": task_info.get("confirmed_receiver_id", ""),
            "completed_time": "",
        }

        # 写入CSV
        fieldnames = [
            "task_id",
            "creator_id",
            "creator_name",
            "assigned_to_id",
            "assigned_to_name",
            "status",
            "created_time",
            "risk_summary",
            "risk_data_url",
            "suggested_receiver_id",
            "confirmed_receiver_id",
            "completed_time",
        ]

        file_exists = tasks_file.exists()
        with open(tasks_file, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(task_row)

        logger.info(f"[ManagerAgent] 任务创建成功: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "message": f"任务 {task_id} 创建成功！",
        }


# 便捷函数
async def create_manager_agent(user_id: str, user_name: str) -> ManagerAgent:
    """创建主智能体实例"""
    agent = ManagerAgent(user_id, user_name)
    await agent.__aenter__()
    return agent
