"""
子智能体（Staff Agent）- IM端一线人员使用
重构后：使用Skill+工具混合架构，SDK自主路由
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
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


class StaffAgent:
    """
    子智能体 - 一线人员使用

    重构后特点：
    1. 统一chat()入口，SDK自主理解意图
    2. 注册所有工具+Skill，SDK自主选择调用
    3. IM风格对话，灵活自然
    """

    def __init__(self, user_id: str, user_name: str):
        """
        初始化子智能体

        Args:
            user_id: 用户ID（一线人员ID）
            user_name: 用户名称
        """
        self.user_id = user_id
        self.user_name = user_name
        self.current_task_id: Optional[str] = None
        self.client: Optional[ClaudeSDKClient] = None

        # 加载工具和Skill
        self._tools = self._load_tools()
        self._skills = self._load_skills()

        # 构建System Prompt
        self._system_prompt = self._build_system_prompt()

        # SDK配置
        self._options = self._build_options()

        logger.info(f"[StaffAgent] 初始化: user_id={user_id}, user_name={user_name}")
        logger.info(f"[StaffAgent] 加载工具: {len(self._tools)}个")
        logger.info(f"[StaffAgent] 加载Skill: {len(self._skills)}个")

    def _load_tools(self) -> Dict:
        """加载所有原子工具"""
        from .tools import ALL_TOOLS

        return ALL_TOOLS

    def _load_skills(self) -> Dict:
        """加载所有Skill"""
        from .skills import get_all_skills

        return get_all_skills()

    def _build_system_prompt(self) -> str:
        """构建System Prompt"""

        skill_descriptions = []
        for name, skill in self._skills.items():
            skill_descriptions.append(f"- {name}: {skill.description}")

        system_prompt = f"""你是一个风险核查助手，负责协助一线人员完成风险核查工作。

## 你的能力

### Skill（业务能力）
{chr(10).join(skill_descriptions)}

### 工具（原子能力）
- get_task_detail: 获取任务详情
- parse_pdf/parse_word: 解析上传文件
- update_task_status: 更新任务状态
- save_chat_message: 保存聊天记录

## 工作方式

用户会用自然语言与你交流，你自己判断需要做什么，然后自主调用合适的Skill或工具来完成。

主动推送任务信息，指导用户完成核查工作。

## 任务状态流转规则

### 任务状态说明
- **已创建**：任务刚创建，尚未下发
- **已下发**：任务已分配给您，等待您反馈
- **反馈中**：您开始处理任务，正在提交材料或进行核查
- **反馈完成**：您已完成核查，提交了反馈
- **已超时**：未在规定时间内完成反馈

### 时间规则
- 日度任务：反馈截止时间 = 下发时间 + 24小时
- 月度任务：反馈截止时间 = 下发时间 + 72小时

### 重要提示
1. 任务创建后，需要等待业务负责人下发任务（assign_task），您才会收到"已下发"状态的通知
2. 您的首次消息会触发系统记录 sent_time（如果尚未设置）
3. 当您确认完成核查后，系统会自动将任务状态更新为"反馈完成"
4. 请注意任务截止时间，在截止前完成反馈

## 当前用户
- 用户ID: {self.user_id}
- 用户名: {self.user_name}
- 角色: 一线操作人员

"""
        return system_prompt

    def _build_options(self) -> ClaudeSDKClient:
        """构建SDK配置"""

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
            max_turns=20,
            thinking={"type": "enabled", "budget_tokens": 20000},
            tools=available,
        )

    async def __aenter__(self):
        """异步上下文入口"""
        self.client = ClaudeSDKClient(options=self._options)
        await self.client.__aenter__()
        logger.info(f"[StaffAgent] 会话启动: {self.user_name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            logger.info(f"[StaffAgent] 会话关闭: {self.user_name}")

    async def init_task(self, task_id: str) -> str:
        """
        初始化任务，推送任务信息

        Args:
            task_id: 任务ID

        Returns:
            推送的任务信息
        """
        logger.info(f"[StaffAgent] 初始化任务: {task_id}")
        self.current_task_id = task_id

        # 首次调用时设置 sent_time 和 feedback_deadline
        from .tools import get_task_detail, update_task_status
        from datetime import datetime, timedelta

        task_info = get_task_detail(task_id)
        if task_info:
            current_time = datetime.now()
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

            # 根据任务类型设置 feedback_deadline
            task_type = task_info.get("task_type", "日度")
            if task_type == "月度":
                # 月度任务：72小时
                deadline_hours = 72
            else:
                # 日度任务（默认）：24小时
                deadline_hours = 24

            deadline_time = current_time + timedelta(hours=deadline_hours)
            deadline_str = deadline_time.strftime("%Y-%m-%d %H:%M:%S")

            # 如果任务没有 sent_time，设置它
            if not task_info.get("sent_time"):
                update_task_status(
                    task_id,
                    "反馈中",
                    "",
                    sent_time=current_time_str,
                    feedback_deadline=deadline_str
                )
                logger.info(f"[StaffAgent] 首次初始化，已设置 sent_time={current_time_str}, feedback_deadline={deadline_str}")
            elif not task_info.get("feedback_deadline"):
                # 如果有 sent_time 但没有 feedback_deadline，也设置它
                update_task_status(
                    task_id,
                    "反馈中",
                    "",
                    feedback_deadline=deadline_str
                )
                logger.info(f"[StaffAgent] 已设置 feedback_deadline={deadline_str}")

        # 使用Skill获取任务信息
        from .skills import get_skill

        guider_skill = get_skill("核查_guider")

        if guider_skill:
            result = await guider_skill.execute(
                {"task_id": task_id},
                {"user_id": self.user_id, "user_name": self.user_name},
            )

            if result.get("success"):
                guidance = result.get("guidance", {})
                welcome = f"""您好！您有新任务需要核查：

{guidance.get("task_intro", "")}

{chr(10).join(guidance.get("steps", []))}

如有疑问，请随时问我！"""
                return welcome

        # 兼容旧逻辑
        return f"任务 {task_id} 已接收，请开始核查工作。"

    async def chat(self, message: str) -> str:
        """
        处理一线人员消息 - 统一入口

        Args:
            message: 一线人员消息

        Returns:
            Agent回复
        """
        logger.info(f"[StaffAgent] 收到消息: {message[:100]}...")

        # 检查是否是首次调用（sent_time为空），如果是则记录当前时间
        if self.current_task_id:
            from .tools import get_task_detail

            task_info = get_task_detail(self.current_task_id)
            if task_info and not task_info.get("sent_time"):
                # 首次调用，记录sent_time
                from .tools import update_task_status

                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                update_task_status(
                    self.current_task_id,
                    "反馈中",
                    "",
                    sent_time=current_time
                )
                logger.info(f"[StaffAgent] 首次对话，已记录sent_time: {current_time}")

        # 构建prompt
        prompt = f"""当前用户：{self.user_name} (ID: {self.user_id})
当前任务ID：{self.current_task_id or "无"}

一线人员消息：{message}

请根据任务要求回复用户，指导其完成核查工作。

重要提示：
1. 如果用户表示已完成核查任务（如说"完成了"、"已经核实完毕"、"确认完成"等），请调用update_task_status工具将任务状态更新为"反馈完成"，并生成反馈总结。
2. 在调用update_task_status时，需要提供清晰的反馈总结，说明核查的结果和结论。"""

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
                logger.info(f"[StaffAgent] 请求完成: {msg.subtype}")

        reply = "\n".join(responses) if responses else "好的，请继续。"

        logger.info(f"[StaffAgent] 回复: {reply[:100]}...")
        return reply

    async def handle_file_upload(self, file_path: str, file_name: str) -> str:
        """
        处理文件上传 - 兼容旧接口

        Args:
            file_path: 文件路径
            file_name: 文件名

        Returns:
            验证结果
        """
        logger.info(f"[StaffAgent] 处理文件上传: {file_name}")

        # 解析文件
        from .tools import parse_file

        result = parse_file(file_path)

        if "error" in result:
            return f"文件处理失败: {result['error']}"

        # 保存到反馈
        if self.current_task_id:
            from .tools import save_uploaded_file_from_path

            save_result = save_uploaded_file_from_path(
                self.current_task_id, file_path, file_name
            )

        return f"""✅ 文件已收到：{file_name}

{result.get("summary", "")}

请继续完成核查，如有更多材料需要上传，请告诉我！"""

    async def complete_task(self) -> Dict[str, Any]:
        """
        完成任务 - 兼容旧接口

        Returns:
            反馈总结
        """
        if not self.current_task_id:
            return {"error": "没有当前任务"}

        # 使用Skill生成总结
        from .skills import get_skill

        summary_skill = get_skill("summary_generator")

        if summary_skill:
            result = await summary_skill.execute(
                {"task_id": self.current_task_id, "auto_complete": True},
                {"user_id": self.user_id, "user_name": self.user_name},
            )
            return result

        return {"error": "总结生成失败"}
    async def notify_new_task(self, task_id: str, task_info: dict) -> dict:
        """
        发送新任务通知给用户 - 核心功能

        当Staff端收到新任务推送时，调用此方法让Agent主动发送消息引导用户

        Args:
            task_id: 任务ID
            task_info: 任务信息

        Returns:
            发送结果
        """
        logger.info(f"[StaffAgent] >>> notify_new_task 开始: task_id={task_id}, user_id={self.user_id}")
        logger.info(f"[StaffAgent] 任务信息: {task_info}")

        try:
            # 1. 先设置当前任务
            self.current_task_id = task_id
            logger.info(f"[StaffAgent] 已设置当前任务: {task_id}")

            # 2. 构建通知提示词
            risk_summary = task_info.get("risk_summary", "未知")
            task_type = task_info.get("task_type", "日度")
            creator_name = task_info.get("creator_name", "未知")

            # 精心设计的提示词 - 与 Staff System Prompt 保持一致
            notification_prompt = f"""【新任务通知】

您有一个新的风险核查任务需要处理！

📋 任务信息：
- 任务编号：{task_id}
- 任务类型：{task_type}
- 创建人：{creator_name}
- 风险摘要：{risk_summary}

请主动发送一条友好的消息，告知用户有新的核查任务。

消息要求：
1. 语气友好、主动
2. 简洁明了地告知任务内容
3. 明确告诉用户**需要提交什么材料**（如：运单截图、签收单据、情况说明等）
4. 引导用户开始提交材料或提问
5. 适当使用emoji让消息更生动

**重要**：你是告知用户需要提交什么材料来完成任务，**不是教用户怎么核查**。

直接回复用户即可，不需要调用工具。"""

            logger.info(f"[StaffAgent] 发送通知消息给用户...")
            logger.info(f"[StaffAgent] 提示词: {notification_prompt[:200]}...")

            # 3. 调用SDK发送消息
            await self.client.query(notification_prompt)

            # 4. 收集回复
            responses = []
            async for msg in self.client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            responses.append(block.text)
                            logger.info(f"[StaffAgent] Agent回复(block): {block.text[:100]}...")
                elif isinstance(msg, ResultMessage):
                    logger.info(f"[StaffAgent] 请求完成: {msg.subtype}")

            reply = "\n".join(responses) if responses else "您好！您有新任务需要核查，请告诉我开始工作。"

            logger.info(f"[StaffAgent] >>> notify_new_task 完成: 回复={reply[:100]}...")

            # 5. 保存聊天记录到数据库
            try:
                from .tools import save_chat_message
                save_chat_message(
                    task_id=task_id,
                    sender="Agent",
                    message=reply,
                    sender_type="agent"
                )
                logger.info(f"[StaffAgent] 聊天记录已保存")
            except Exception as e:
                logger.error(f"[StaffAgent] 保存聊天记录失败: {e}")

            return {
                "success": True,
                "message": reply,
                "task_id": task_id
            }

        except Exception as e:
            logger.error(f"[StaffAgent] >>> notify_new_task 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }



# 便捷函数
async def create_staff_agent(user_id: str, user_name: str) -> "StaffAgent":
    """创建子智能体实例"""
    agent = StaffAgent(user_id, user_name)
    await agent.__aenter__()
    return agent
