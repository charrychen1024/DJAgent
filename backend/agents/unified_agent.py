"""
统一 Agent 核心 - 通过 Config 实例化统一的 ClaudeAgent
完全信任 SDK 的 ReAct 循环，不做任何预处理或手动工具调用
"""

import logging
from typing import Dict, Any, Optional, List
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

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        files: Optional[List[str]] = None,
    ) -> str:
        """
        统一入口 - SDK 自主处理

        用户说什么都可以，SDK 自己判断需要做什么。
        完全信任 SDK 的 ReAct 循环，不做任何干预。

        Args:
            message: 用户消息
            context: 上下文信息（如当前任务ID等）
            files: 上传的文件路径列表

        Returns:
            Agent 回复
        """
        logger.info(f"[UnifiedAgent] 收到消息: {message[:100]}...")
        if files:
            logger.info(f"[UnifiedAgent] 收到文件: {files}")

        # 构建提示词
        prompt = self._build_prompt(message, context, files)

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
                        # 检查是否是文本块（有 text 属性）
                        if hasattr(block, 'text'):
                            text_messages.append(block.text)
                            logger.debug(f"[UnifiedAgent] 文本消息: {block.text[:50]}...")
                        # 检查是否是工具调用（确保有 input 属性）
                        elif hasattr(block, 'type') and block.type == 'tool_use':
                            if hasattr(block, 'name'):
                                tool_messages.append(f"工具调用: {block.name}")
                                logger.debug(f"[UnifiedAgent] 工具调用: {block.name}")
                                if hasattr(block, 'input'):
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

    def _build_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        files: Optional[List[str]] = None,
    ) -> str:
        """构建提示词"""
        prompt = f"""当前用户：{self.config.user_name} (ID: {self.config.user_id})
角色：{"业务负责人" if self.config.mode == "manager" else "一线操作人员"}
"""

        # 添加上传文件信息
        if files:
            prompt += "\n用户上传了以下文件：\n"
            for i, file_path in enumerate(files, 1):
                # 提取文件名
                import os
                filename = os.path.basename(file_path)
                prompt += f"{i}. {filename} (路径: {file_path})\n"
            prompt += "请根据文件类型选择合适的解析工具（parse_csv, parse_excel, parse_pdf, parse_word）来读取文件内容。\n"

        if context:
            if context.get("task_id"):
                prompt += f"\n当前任务ID：{context.get('task_id')}\n"
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
        from datetime import datetime, timedelta

        task_detail = get_task_detail(task_id)

        if "error" in task_detail:
            return f"任务 {task_id} 不存在"

        # 获取任务数据（从 task_detail["task"] 中获取）
        task_data = task_detail.get("task", {})

        # 首次调用时设置 sent_time 和 feedback_deadline（只有未下发时才设置）
        if not task_data.get("sent_time"):
            current_time = datetime.now()
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

            # 根据任务类型设置 feedback_deadline
            task_type = task_data.get("task_type", "日度")
            deadline_hours = 72 if task_type == "月度" else 24
            deadline_time = current_time + timedelta(hours=deadline_hours)
            deadline_str = deadline_time.strftime("%Y-%m-%d %H:%M:%S")

            # 更新任务
            from .tools import update_task_status
            update_result = update_task_status(
                task_id,
                "反馈中",
                "",
                sent_time=current_time_str,
                feedback_deadline=deadline_str
            )
            logger.info(f"[UnifiedAgent] 首次初始化，已设置 sent_time={current_time_str}, feedback_deadline={deadline_str}")

            # 更新task_data以便返回正确的feedback_deadline
            task_data["sent_time"] = current_time_str
            task_data["feedback_deadline"] = deadline_str

        # 生成欢迎消息
        welcome = f"""您好！您有新任务需要核查：

**任务ID**: {task_id}
**风险摘要**: {task_data.get("risk_summary", "无")}
**创建人**: {task_data.get("creator_name", "未知")}
**截止时间**: {task_data.get("feedback_deadline", "未设置")}

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
        logger.info(f"[UnifiedAgent] >>> notify_new_task 开始: task_id={task_id}, user_id={self.config.user_id}")
        logger.info(f"[UnifiedAgent] 任务信息: {task_info}")

        try:
            # 1. 先设置当前任务
            self.current_task_id = task_id
            logger.info(f"[UnifiedAgent] 已设置当前任务: {task_id}")

            # 2. 构建通知提示词
            risk_summary = task_info.get("risk_summary", "未知")
            task_type = task_info.get("task_type", "日度")
            creator_name = task_info.get("creator_name", "未知")
            feedback_deadline = task_info.get("feedback_deadline", "")

            # 精心设计的提示词 - 与 Staff System Prompt 保持一致
            deadline_display = ""
            if feedback_deadline:
                # 转换时间格式为更友好的显示
                try:
                    from datetime import datetime
                    dt = datetime.strptime(feedback_deadline, "%Y-%m-%d %H:%M:%S")
                    deadline_display = f"请在 {dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d} 前完成反馈"
                except:
                    deadline_display = f"请在 {feedback_deadline} 前完成反馈"
            else:
                deadline_display = "请尽快完成反馈"

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
6. **{deadline_display}** - 必须直接使用这个时间，不要自己编造！

**重要**：你是告知用户需要提交什么材料来完成任务，**不是教用户怎么核查**。

========================================
【表单生成约束】- **必须执行，不可跳过**

在您的回复末尾，必须添加以下JSON格式的核查表单定义。使用```json和```包装，格式如下：

```json
{{
  "form_id": "form_check_000-20260325155513",
  "title": "核查信息收集表",
  "description": "请填写以下信息完成核查",
  "state": "editable",
  "sections": [
    {{
      "title": "任务基本信息",
      "fields": [
        {{
          "id": "task_id",
          "label": "任务编号",
          "type": "text",
          "required": true,
          "readonly": true,
          "value": "{task_id}"
        }}
      ]
    }},
    {{
      "title": "核查材料提交",
      "fields": [
        {{
          "id": "photos",
          "label": "现场照片",
          "type": "file_upload",
          "required": true,
          "accept": "image/*"
        }},
        {{
          "id": "materials",
          "label": "相关单据",
          "type": "file_upload",
          "required": false,
          "accept": ".pdf,.doc,.docx,.jpg,.jpeg,.png"
        }},
        {{
          "id": "notes",
          "label": "核查说明",
          "type": "textarea",
          "required": false,
          "placeholder": "请输入核查的详细情况...",
          "validation": {{"maxLength": 500}}
        }}
      ]
    }}
  ]
}}
```

⚠️ **重要提示**：
- 表单JSON必须直接出现在回复末尾，用```json```包装
- form_id 格式：form_check_ + 任务编号前15位
- 必需字段：form_id、title、state、sections（缺一不可）
- 根据实际任务类型动态调整字段（不要照搬模板，要定制）
- JSON 必须完全有效且可被解析
- 表单必须包含任务编号readonly字段，引导用户上传相关材料

========================================

现在请按照上述要求发送友好的任务通知消息，同时在末尾附加表单 JSON。"""

            logger.info(f"[UnifiedAgent] 发送通知消息给用户...")
            logger.info(f"[UnifiedAgent] 提示词: {notification_prompt[:200]}...")

            # 3. 调用SDK发送消息（增加超时和错误处理）
            try:
                await self.client.query(notification_prompt)

                # 4. 收集回复
                responses = []
                async for msg in self.client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                responses.append(block.text)
                                logger.info(f"[UnifiedAgent] Agent回复(block): {block.text[:100]}...")
                    elif isinstance(msg, ResultMessage):
                        logger.info(f"[UnifiedAgent] 请求完成: {msg.subtype}")

                reply = "\n".join(responses) if responses else ""

                # 消息发送成功后，设置 sent_time 和状态为"已下发"
                if reply:
                    from datetime import datetime
                    from .tools import update_task_status
                    sent_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    update_result = update_task_status(
                        task_id,
                        "已下发",  # 设置状态为"已下发"
                        "",
                        sent_time=sent_time_str  # 设置 sent_time，不修改 feedback_deadline 保护已有值
                    )
                    logger.info(f"[UnifiedAgent] 消息发送成功，已设置 sent_time={sent_time_str}, status=已下发")

            except Exception as e:
                logger.error(f"[UnifiedAgent] LLM 调用失败: {e}")
                reply = ""

            # 如果没有获取到回复，使用默认消息
            if not reply:
                reply = f"""您好！您有新任务需要处理！

📋 任务编号：{task_id}
📝 风险摘要：{task_info.get('risk_summary', '无')}
👤 创建人：{task_info.get('creator_name', '未知')}

请开始核查工作，如有疑问，随时问我！"""
                logger.info(f"[UnifiedAgent] 使用默认消息")

            logger.info(f"[UnifiedAgent] >>> notify_new_task 完成: 回复={reply[:100]}...")

            # 6. 从回复中提取表单JSON (Fix 1+2: JSON Extraction)
            import re
            import json

            text_message = reply
            form_schema = None
            form_id = None
            message_type = "text"

            # 尝试从markdown代码块中提取JSON表单定义
            pattern = r'```json\s*([\s\S]*?)\s*```'
            match = re.search(pattern, reply)

            if match:
                json_text = match.group(1).strip()
                try:
                    schema = json.loads(json_text)
                    # 验证必需字段
                    if all(key in schema for key in ['form_id', 'title', 'state', 'sections']):
                        form_schema = schema
                        form_id = schema.get('form_id')
                        message_type = "form_card"
                        # 移除JSON代码块，仅保留文本消息
                        text_message = re.sub(pattern, '', reply).strip()
                        logger.info(f"[UnifiedAgent] 成功提取表单: form_id={form_id}, message_type={message_type}")
                    else:
                        logger.warning(f"[UnifiedAgent] 表单JSON缺少必需字段")
                except json.JSONDecodeError as e:
                    logger.warning(f"[UnifiedAgent] JSON解析失败: {e}")

            logger.debug(f"[UnifiedAgent] 消息类型: {message_type}, 文本长度: {len(text_message)}")

            # 7. 保存聊天记录到数据库 (保存纯文本部分和表单信息)
            try:
                from .tools import save_chat_message
                # Fix 14: 传入表单信息到保存函数
                save_chat_message(
                    task_id=task_id,
                    sender="Agent",
                    message=text_message,
                    sender_type="agent",
                    message_type=message_type,  # 传入消息类型
                    schema=form_schema,          # 传入表单schema
                    form_id=form_id              # 传入表单ID
                )
                logger.info(f"[UnifiedAgent] 聊天记录已保存，包括表单数据")
            except Exception as e:
                logger.error(f"[UnifiedAgent] 保存聊天记录失败: {e}")

            # 8. 返回结构化数据 (Fix 2: New Return Structure)
            from datetime import datetime as dt
            return {
                "success": True,
                "type": message_type,
                "message": text_message,
                "schema": form_schema,
                "form_id": form_id,
                "task_id": task_id,
                "timestamp": dt.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[UnifiedAgent] >>> notify_new_task 失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }


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
