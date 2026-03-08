"""
统一 Agent 核心 - 通过 Config 实例化统一的 ClaudeAgent
完全信任 SDK 的 ReAct 循环，不做任何预处理或手动工具调用
"""

import logging
from typing import Dict, Any, Optional
from claude_agent_sdk import ClaudeSDKClient, AssistantMessage, TextBlock, ResultMessage

from .config import AgentConfig

logger = logging.getLogger(__name__)


class UnifiedAgent:
    """
    统一 Agent 核心

    特点：
    1. 通过 AgentConfig 配置，支持 Manager 和 Staff 两种模式
    2. 完全信任 SDK 的 ReAct 循环
    3. 不做任何预处理或手动工具调用
    4. 统一的 chat() 入口
    """

    def __init__(self, config: AgentConfig):
        """
        初始化统一 Agent

        Args:
            config: Agent 配置
        """
        self.config = config
        self.client: Optional[ClaudeSDKClient] = None
        self.current_task_id: Optional[str] = None

        # 构建配置
        self._options = config.to_sdk_options()

        logger.info(
            f"[UnifiedAgent] 初始化: mode={config.mode}, user={config.user_name}"
        )

    async def __aenter__(self):
        """异步上下文入口"""
        self.client = ClaudeSDKClient(options=self._options)
        await self.client.__aenter__()
        logger.info(f"[UnifiedAgent] 会话启动: {self.config.user_name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            logger.info(f"[UnifiedAgent] 会话关闭: {self.config.user_name}")

    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        统一入口 - SDK 自主处理

        用户说什么都可以，SDK 自己判断需要做什么。
        完全信任 SDK 的 ReAct 循环，不做任何干预。

        Args:
            message: 用户消息
            context: 上下文信息（如当前任务ID等）

        Returns:
            Agent 回复
        """
        logger.info(f"[UnifiedAgent] 收到消息: {message[:100]}...")

        # 构建提示词
        prompt = self._build_prompt(message, context)

        # 发送 SDK 处理
        await self.client.query(prompt)
        
        # 收集所有回复（包括所有类型）
        all_messages = []
        async for msg in self.client.receive_response():
            all_messages.append(msg)
        
        logger.info(f"[UnifiedAgent] 收到 {len(all_messages)} 条消息")
        
        # 从消息中提取文本内容
        text_messages = []
        tool_messages = []
        for msg in all_messages:
            if isinstance(msg, AssistantMessage):
                if hasattr(msg, 'content') and hasattr(msg, 'model'):
                    logger.debug(f"[UnifiedAgent] AssistantMessage model={msg.model}")
                if hasattr(msg.content, '__iter__'):
                    for block in msg.content:
                        if hasattr(block, 'type') and block.type == 'text':
                            if hasattr(block, 'text'):
                                text_messages.append(block.text)
                            logger.debug(f"[UnifiedAgent] 文本消息: {block.text[:50]}...")
                        elif hasattr(block, 'type') and block.type == 'tool_use':
                            if hasattr(block, 'name') and hasattr(block, 'input'):
                                tool_messages.append(f"工具调用: {block.name}")
                                logger.debug(f"[UnifiedAgent] 工具调用: {block.name}")
                    logger.debug(f"[UnifiedAgent] 输入参数: {block.input}")

            if isinstance(msg, ResultMessage):
                logger.info(f"[UnifiedAgent] 结果消息: {msg.subtype}")
        
        # 返回所有文本消息
        if text_messages:
            reply = "\n".join(text_messages)
            logger.info(f"[UnifiedAgent] 回复长度: {len(reply)} 字符")
            logger.info(f"[UnifiedAgent] 回复前100字: {reply[:100]}...")
        else:
            # 没有文本消息，可能是只有工具调用
            reply = "我已收到您的请求，正在处理中..."
            logger.info("[UnifiedAgent] 只有工具调用，无文本消息")
        
        return reply

        reply = "\n".join(responses) if responses else "好的，请继续。"

        logger.info(f"[UnifiedAgent] 回复: {reply[:100]}...")
        return reply

    def _build_prompt(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """构建提示词"""
        prompt = f"""当前用户：{self.config.user_name} (ID: {self.config.user_id})
角色：{"业务负责人" if self.config.mode == "manager" else "一线操作人员"}
"""

        if context:
            if context.get("task_id"):
                prompt += f"当前任务ID：{context.get('task_id')}\n"
                self.current_task_id = context.get("task_id")
            if context.get("risk_data"):
                prompt += f"风险数据：{context.get('risk_data')}\n"

        prompt += f"\n用户消息：{message}\n\n"

        if self.config.mode == "manager":
            prompt += "请根据用户需求，调用合适的工具完成任务。"
        elif self.config.mode == "staff":
            prompt += "请根据任务要求回复用户，指导其完成核查工作。"

        return prompt

    async def init_task(self, task_id: str) -> str:
        """
        初始化任务（Staff 模式专用）

        Args:
            task_id: 任务 ID

        Returns:
            推送的任务信息
        """
        if self.config.mode != "staff":
            logger.warning(
                f"[UnifiedAgent] init_task 只在 Staff 模式下可用，当前模式: {self.config.mode}"
            )
            return ""

        logger.info(f"[UnifiedAgent] 初始化任务: {task_id}")
        self.current_task_id = task_id

        # 获取任务详情
        from .tools import get_task_detail

        task_detail = get_task_detail(task_id)

        if "error" in task_detail:
            return f"任务 {task_id} 不存在"

        # 生成欢迎消息
        welcome = f"""您好！您有新任务需要核查：

**任务ID**: {task_id}
**风险摘要**: {task_detail.get("risk_summary", "无")}
**创建人**: {task_detail.get("creator_name", "未知")}
**创建时间**: {task_detail.get("created_at", "未知")}

请开始核查工作，如有疑问，随时问我！"""

        return welcome

    async def handle_file_upload(self, file_path: str, file_name: str) -> str:
        """
        处理文件上传（Staff 模式专用）

        Args:
            file_path: 文件路径
            file_name: 文件名

        Returns:
            处理结果
        """
        if self.config.mode != "staff":
            logger.warning(
                f"[UnifiedAgent] handle_file_upload 只在 Staff 模式下可用，当前模式: {self.config.mode}"
            )
            return ""

        logger.info(f"[UnifiedAgent] 处理文件上传: {file_name}")

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
        完成任务（Staff 模式专用）

        Returns:
            反馈总结
        """
        if self.config.mode != "staff":
            logger.warning(
                f"[UnifiedAgent] complete_task 只在 Staff 模式下可用，当前模式: {self.config.mode}"
            )
            return {"error": "当前模式不支持此操作"}

        if not self.current_task_id:
            return {"error": "没有当前任务"}

        # 更新任务状态
        from .tools import update_task_status

        update_result = update_task_status(self.current_task_id, "已完成")

        return update_result


async def create_unified_agent(
    config: AgentConfig, auto_start: bool = True
) -> UnifiedAgent:
    """
    创建统一 Agent 实例

    Args:
        config: Agent 配置
        auto_start: 是否自动启动会话

    Returns:
        UnifiedAgent 实例
    """
    agent = UnifiedAgent(config)
    if auto_start:
        await agent.__aenter__()
    return agent
