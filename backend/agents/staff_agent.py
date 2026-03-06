"""
子智能体（Staff Agent）- IM端一线人员使用
负责：接收任务、推送消息给一线人员、指导上传材料、确认完成
"""

import os
import json
import csv
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

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent / "data"


# System Prompt - 子智能体
STAFF_SYSTEM_PROMPT = """You are a risk check assistant Agent.

IMPORTANT RULES:
- Reply in Chinese (use Simplified Chinese)
- Be detailed and helpful
- Give specific guidance to users

Your responsibilities:
1. Push task info and risk data to staff
2. Guide staff through verification process
3. Help verify uploaded files
4. Answer questions about tasks
5. Help complete tasks

You have tools:
- parse_pdf: parse PDF files
- parse_word: parse Word files  
- get_task_detail: get task details

Workflow:
1. User enters -> push task info
2. User replies -> give guidance
3. User uploads files -> verify
4. User confirms -> generate summary

Always reply in detail and help users complete their verification work.
1. 主动推送任务信息和风险数据给一线人员
2. 指导一线人员完成风险核查流程
3. 协助一线人员上传和验证核查文件
4. 回答一线人员关于风险任务的问题
5. 帮助一线人员完成任务提交和总结

你具备以下工具能力：
- parse_pdf: 解析PDF证明文件
- parse_word: 解析Word证明文件
- get_task_detail: 获取当前任务详情和风险数据
- verify_file: 验证上传文件是否符合要求

工作流程：
1. 用户进入 → 你推送任务信息
2. 用户回复核查情况 → 你引导下一步
3. 用户上传文件 → 你验证文件
4. 用户确认完成 → 你生成反馈总结

请以友好、专业的语气与一线人员对话，提供清晰的指导和支持。
"""


def build_staff_options() -> ClaudeAgentOptions:
    """构建子智能体配置"""
    from .tools import AGENT_TOOLS

    return ClaudeAgentOptions(
        env={
            "ANTHROPIC_BASE_URL": os.getenv(
                "ANTHROPIC_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding"
            ),
            "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN", ""),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        },
        system_prompt=STAFF_SYSTEM_PROMPT,
        permission_mode="acceptEdits",
        max_turns=15,
        thinking={"type": "disabled"},
        tools=[tool.__name__ for tool in AGENT_TOOLS],
    )


class StaffAgent:
    """
    子智能体 - 一线人员使用
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
        self.options = build_staff_options()
        logger.info(f"[StaffAgent] 初始化: user_id={user_id}, user_name={user_name}")

    async def __aenter__(self):
        """异步上下文入口"""
        self.client = ClaudeSDKClient(options=self.options)
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

        # 获取任务详情
        task_detail = self._get_task_detail(task_id)

        if "error" in task_detail:
            return f"获取任务失败: {task_detail['error']}"

        task = task_detail.get("task", {})

        # 构建推送消息
        welcome_msg = f"""您好！您有新任务需要核查：

📋 任务ID：{task.get("task_id", "")}
📝 风险简述：{task.get("risk_summary", "")}
👤 创建人：{task.get("creator_name", "")}
📅 创建时间：{task.get("created_time", "")}

请根据风险描述进行核查，并在完成后上传相关证明材料。

如有疑问，请随时问我！"""

        logger.info(f"[StaffAgent] 推送任务信息: {task_id}")
        return welcome_msg

    def _get_task_detail(self, task_id: str) -> Dict[str, Any]:
        """获取任务详情"""
        try:
            # 读取任务CSV
            tasks_file = DATA_DIR / "tasks.csv"
            if not tasks_file.exists():
                return {"error": "任务文件不存在"}

            with open(tasks_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("task_id") == task_id:
                        # 读取反馈JSON
                        feedback_file = DATA_DIR / "feedback" / f"{task_id}.json"
                        feedback = {}
                        if feedback_file.exists():
                            with open(feedback_file, "r", encoding="utf-8") as ff:
                                feedback = json.load(ff)

                        return {"success": True, "task": row, "feedback": feedback}

            return {"error": f"任务不存在: {task_id}"}

        except Exception as e:
            logger.error(f"[StaffAgent] 获取任务详情失败: {str(e)}")
            return {"error": str(e)}

    async def chat(self, message: str) -> str:
        """
        处理一线人员消息

        Args:
            message: 一线人员消息

        Returns:
            Agent回复
        """
        logger.info(f"[StaffAgent] 收到消息: {message[:100]}...")

        # 构建prompt
        prompt = f"""当前用户：{self.user_name} (ID: {self.user_id})
当前任务ID：{self.current_task_id or "无"}

一线人员消息：{message}

请根据任务要求回复用户，指导其完成核查工作。"""

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
                logger.info(f"[StaffAgent] 请求完成: {msg.subtype}")

        reply = "\n".join(responses) if responses else "好的，请继续。"

        logger.info(f"[StaffAgent] 回复: {reply[:100]}...")
        return reply

    async def handle_file_upload(self, file_path: str, file_name: str) -> str:
        """
        处理文件上传

        Args:
            file_path: 文件路径
            file_name: 文件名

        Returns:
            验证结果
        """
        logger.info(f"[StaffAgent] 处理文件上传: {file_name}")

        # 解析文件
        if file_name.endswith(".pdf"):
            result = self._parse_pdf(file_path)
        elif file_name.endswith((".docx", ".doc")):
            result = self._parse_word(file_path)
        elif file_name.endswith((".jpg", ".jpeg", ".png")):
            result = self._parse_image(file_path)
        else:
            result = {"success": True, "summary": f"已收到文件: {file_name}"}

        if "error" in result:
            logger.error(f"[StaffAgent] 文件解析失败: {result['error']}")
            return f"文件上传失败: {result['error']}"

        # 保存到反馈
        await self._save_uploaded_file(file_name, file_path, result)

        reply = f"""✅ 文件已收到：{file_name}

{result.get("summary", "")}

请继续完成核查，如有更多材料需要上传，请告诉我！"""

        logger.info(f"[StaffAgent] 文件处理完成: {file_name}")
        return reply

    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """解析PDF"""
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for i, page in enumerate(reader.pages[:3]):  # 只读前3页
                    text += page.extract_text() or ""

            return {
                "success": True,
                "type": "pdf",
                "pages": len(reader.pages),
                "text": text[:2000],
                "summary": f"PDF文件包含{len(reader.pages)}页",
            }
        except Exception as e:
            return {"error": f"PDF解析失败: {str(e)}"}

    def _parse_word(self, file_path: str) -> Dict[str, Any]:
        """解析Word"""
        try:
            import docx

            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

            return {
                "success": True,
                "type": "word",
                "paragraphs": len(paragraphs),
                "text": "\n".join(paragraphs[:10]),
                "summary": f"Word文档包含{len(paragraphs)}段",
            }
        except Exception as e:
            return {"error": f"Word解析失败: {str(e)}"}

    def _parse_image(self, file_path: str) -> Dict[str, Any]:
        """解析图片（简单处理）"""
        import os

        size = os.path.getsize(file_path)

        return {
            "success": True,
            "type": "image",
            "size": size,
            "summary": f"图片文件，大小{size / 1024:.1f}KB",
        }

    async def _save_uploaded_file(
        self, file_name: str, file_path: str, parse_result: Dict
    ):
        """保存上传的文件信息"""
        if not self.current_task_id:
            return

        try:
            feedback_file = DATA_DIR / "feedback" / f"{self.current_task_id}.json"

            feedback_data = {}
            if feedback_file.exists():
                with open(feedback_file, "r", encoding="utf-8") as f:
                    feedback_data = json.load(f)

            if "uploaded_files" not in feedback_data:
                feedback_data["uploaded_files"] = []

            feedback_data["uploaded_files"].append(
                {
                    "filename": file_name,
                    "file_path": file_path,
                    "parse_result": parse_result,
                }
            )

            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(feedback_data, f, ensure_ascii=False, indent=2)

            logger.info(f"[StaffAgent] 文件信息已保存: {file_name}")

        except Exception as e:
            logger.error(f"[StaffAgent] 保存文件信息失败: {str(e)}")

    async def complete_task(self) -> Dict[str, Any]:
        """
        完成任务

        Returns:
            反馈总结
        """
        if not self.current_task_id:
            return {"error": "没有当前任务"}

        logger.info(f"[StaffAgent] 完成任务: {self.current_task_id}")

        # 获取任务详情
        task_detail = self._get_task_detail(self.current_task_id)

        if "error" in task_detail:
            return {"error": task_detail["error"]}

        # 生成反馈总结
        prompt = f"""请根据以下信息生成任务反馈总结：

任务信息：
- 任务ID：{self.current_task_id}
- 风险简述：{task_detail["task"].get("risk_summary", "")}

上传的文件：
{json.dumps(task_detail.get("feedback", {}).get("uploaded_files", []), ensure_ascii=False, indent=2)}

请生成简洁的反馈总结，包括：
1. 核查结果
2. 发现的问题
3. 建议措施
"""

        await self.client.query(prompt)

        responses = []
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        responses.append(block.text)

        summary = "\n".join(responses) if responses else "任务已完成"

        # 更新任务状态
        self._update_task_status(self.current_task_id, "反馈完成", summary)

        logger.info(f"[StaffAgent] 任务完成: {self.current_task_id}")

        return {
            "success": True,
            "task_id": self.current_task_id,
            "feedback_summary": summary,
            "message": "✅ 任务已完成！反馈总结已生成。",
        }

    def _update_task_status(self, task_id: str, status: str, summary: str = ""):
        """更新任务状态"""
        try:
            tasks_file = DATA_DIR / "tasks.csv"
            rows = []

            with open(tasks_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row.get("task_id") == task_id:
                        row["status"] = status
                        if status == "反馈完成":
                            from datetime import datetime

                            row["completed_time"] = datetime.now().strftime(
                                "%Y-%m-%d %H:%M"
                            )
                    rows.append(row)

            with open(tasks_file, "w", encoding="utf-8", newline="") as f:
                if fieldnames:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

            # 更新反馈文件
            if summary:
                feedback_file = DATA_DIR / "feedback" / f"{task_id}.json"
                feedback_data = {}
                if feedback_file.exists():
                    with open(feedback_file, "r", encoding="utf-8") as f:
                        feedback_data = json.load(f)

                feedback_data["feedback_summary"] = summary
                from datetime import datetime

                feedback_data["summary_timestamp"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                feedback_data["status"] = status

                with open(feedback_file, "w", encoding="utf-8") as f:
                    json.dump(feedback_data, f, ensure_ascii=False, indent=2)

            logger.info(f"[StaffAgent] 任务状态已更新: {task_id} -> {status}")

        except Exception as e:
            logger.error(f"[StaffAgent] 更新任务状态失败: {str(e)}")


# 便捷函数
async def create_staff_agent(user_id: str, user_name: str) -> StaffAgent:
    """创建子智能体实例"""
    agent = StaffAgent(user_id, user_name)
    await agent.__aenter__()
    return agent
