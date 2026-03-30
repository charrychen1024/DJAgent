"""
Claude SDK 消息解析器 - 将 Claude SDK StreamEvent 转换为 SSE 格式

Claude Agent SDK 的 StreamEvent 已经包含标准化的 event 数据，
我们只需要将其转换为 SSE 格式即可。
"""

import json
import logging
from typing import AsyncIterator, Any, Dict, Optional

from claude_agent_sdk import StreamEvent, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)


def stream_event_to_sse(event: StreamEvent) -> str:
    """
    将 StreamEvent 转换为 SSE 格式

    Args:
        event: StreamEvent 对象

    Returns:
        str: SSE 格式字符串
    """
    event_type = event.event.get('type', 'unknown')

    # 直接使用 event 中的数据
    return f"event: {event_type}\ndata: {json.dumps(event.event, ensure_ascii=False)}\n\n"


def assistant_message_to_sse(msg: AssistantMessage, index: int = 0) -> list:
    """
    将 AssistantMessage 转换为 SSE 格式列表

    Args:
        msg: AssistantMessage 对象
        index: 消息索引

    Returns:
        list: SSE 事件字符串列表
    """
    events = []
    message_id = f"msg_{index}"

    # 消息开始
    events.append(
        f"event: message_start\n"
        f"data: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant', 'content': []}}, ensure_ascii=False)}\n\n"
    )

    # 处理 content blocks
    if hasattr(msg, 'content') and msg.content:
        for i, block in enumerate(msg.content):
            block_type = getattr(block, 'type', 'text')

            if block_type == 'thinking':
                thinking_text = getattr(block, 'thinking', '') or getattr(block, 'thinking_text', '')
                # 思考开始
                events.append(
                    f"event: content_block_start\n"
                    f"data: {json.dumps({'type': 'content_block_start', 'index': i, 'content_block': {'type': 'thinking'}}, ensure_ascii=False)}\n\n"
                )
                # 思考增量
                if thinking_text:
                    events.append(
                        f"event: content_block_delta\n"
                        f"data: {json.dumps({'type': 'content_block_delta', 'index': i, 'delta': {'type': 'thinking_delta', 'thinking': thinking_text}}, ensure_ascii=False)}\n\n"
                    )
                # 思考结束
                events.append(f"event: content_block_stop\ndata: {{'type': 'content_block_stop', 'index': {i}}}\n\n")

            elif block_type == 'tool_use':
                tool_name = getattr(block, 'name', 'unknown')
                tool_input = getattr(block, 'input', {})
                tool_id = getattr(block, 'id', f"tool_{i}")

                # 工具调用开始
                events.append(
                    f"event: content_block_start\n"
                    f"data: {json.dumps({'type': 'content_block_start', 'index': i, 'content_block': {'type': 'tool_use', 'name': tool_name, 'id': tool_id}}, ensure_ascii=False)}\n\n"
                )
                # 工具调用增量
                events.append(
                    f"event: content_block_delta\n"
                    f"data: {json.dumps({'type': 'content_block_delta', 'index': i, 'delta': {'type': 'tool_use_delta', 'name': tool_name, 'input': tool_input, 'tool_use_id': tool_id}}, ensure_ascii=False)}\n\n"
                )
                # 工具调用结束
                events.append(f"event: content_block_stop\ndata: {{'type': 'content_block_stop', 'index': {i}}}\n\n")

            elif block_type == 'text':
                text_content = getattr(block, 'text', '')
                # 文本开始
                events.append(
                    f"event: content_block_start\n"
                    f"data: {json.dumps({'type': 'content_block_start', 'index': i, 'content_block': {'type': 'text'}}, ensure_ascii=False)}\n\n"
                )
                # 文本增量
                if text_content:
                    events.append(
                        f"event: content_block_delta\n"
                        f"data: {json.dumps({'type': 'content_block_delta', 'index': i, 'delta': {'type': 'text_delta', 'text': text_content}}, ensure_ascii=False)}\n\n"
                    )
                # 文本结束
                events.append(f"event: content_block_stop\ndata: {{'type': 'content_block_stop', 'index': {i}}}\n\n")

    # 消息结束
    events.append(
        f"event: message_delta\n"
        f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}}, ensure_ascii=False)}\n\n"
    )
    events.append(f"event: message_stop\ndata: {{'type': 'message_stop'}}\n\n")

    return events


def result_message_to_sse(msg: ResultMessage, index: int = 0) -> list:
    """
    将 ResultMessage 转换为 SSE 格式列表（工具结果）

    Args:
        msg: ResultMessage 对象
        index: 消息索引

    Returns:
        list: SSE 事件字符串列表
    """
    events = []
    tool_use_id = getattr(msg, 'tool_use_id', f"tool_result_{index}")
    content = getattr(msg, 'content', '') or getattr(msg, 'result', '') or ''
    is_error = getattr(msg, 'is_error', False) or hasattr(msg, 'error')

    # 工具结果开始
    events.append(
        f"event: content_block_start\n"
        f"data: {json.dumps({'type': 'content_block_start', 'index': index, 'content_block': {'type': 'tool_result', 'tool_use_id': tool_use_id, 'is_error': is_error}}, ensure_ascii=False)}\n\n"
    )

    # 工具结果内容
    events.append(
        f"event: content_block_delta\n"
        f"data: {json.dumps({'type': 'content_block_delta', 'index': index, 'delta': {'type': 'text_delta', 'text': str(content)}}, ensure_ascii=False)}\n\n"
    )

    # 工具结果结束
    events.append(f"event: content_block_stop\ndata: {{'type': 'content_block_stop', 'index': {index}}}\n\n")

    return events


class SDKMessageParser:
    """
    Claude SDK 消息解析器

    将 SDK 消息转换为标准 SSE 事件流。

    Attributes:
        message_generator: 消息生成器（SDK 的 receive_response）
    """

    def __init__(self, message_generator):
        """
        初始化消息解析器

        Args:
            message_generator: 消息生成器（异步迭代器）
        """
        self.message_generator = message_generator
        self._message_count = 0
        logger.info("[SDKMessageParser] 初始化完成")

    async def parse(self) -> AsyncIterator[str]:
        """
        异步迭代器，返回 SSE 格式事件流

        Yields:
            str: SSE 格式事件字符串
        """
        logger.info("[SDKMessageParser] 开始解析消息")

        has_stream_events = False  # 关键：标记是否已处理 StreamEvent

        async for msg in self.message_generator:
            self._message_count += 1
            msg_type = type(msg).__name__
            logger.debug(f"[SDKMessageParser] 处理消息 #{self._message_count}: {msg_type}")

            if isinstance(msg, StreamEvent):
                has_stream_events = True
                event_type = msg.event.get('type', '')
                logger.debug(f"[SDKMessageParser] StreamEvent type: {event_type}")

                # 处理所有 StreamEvent
                if event_type in ['content_block_delta', 'content_block_start', 'content_block_stop']:
                    # 只输出内容相关事件，跳过 message_start/message_stop（避免重复和重置）
                    yield stream_event_to_sse(msg)

            elif isinstance(msg, AssistantMessage):
                # 关键：如果已经处理过 StreamEvent，就跳过 AssistantMessage（避免重复）
                # StreamEvent 已经包含了所有增量数据，AssistantMessage 是完整汇总，会重复
                if has_stream_events:
                    logger.debug("[SDKMessageParser] 跳过 AssistantMessage（已有 StreamEvent）")
                    continue

                # 只有在没有 StreamEvent 时才处理 AssistantMessage
                logger.debug("[SDKMessageParser] 处理 AssistantMessage（无 StreamEvent）")
                for sse_event in assistant_message_to_sse(msg, self._message_count):
                    yield sse_event

            elif isinstance(msg, ResultMessage):
                # ResultMessage 是工具执行结果，单独处理
                logger.debug("[SDKMessageParser] 处理 ResultMessage")
                for sse_event in result_message_to_sse(msg, self._message_count):
                    yield sse_event

            else:
                logger.debug(f"[SDKMessageParser] 忽略消息类型: {msg_type}")

        logger.info(f"[SDKMessageParser] 解析完成，共 {self._message_count} 条消息")

    def parse_sync(self) -> list:
        """
        同步解析（用于调试）

        Returns:
            list: SSE 事件字符串列表
        """
        events = []
        for msg in self.message_generator:
            if isinstance(msg, StreamEvent):
                events.append(stream_event_to_sse(msg))
            elif isinstance(msg, AssistantMessage):
                events.extend(assistant_message_to_sse(msg))
            elif isinstance(msg, ResultMessage):
                events.extend(result_message_to_sse(msg))
        return events


async def stream_events_as_sse(message_generator) -> AsyncIterator[str]:
    """
    将消息流转换为 SSE 格式流

    Args:
        message_generator: SDK 消息生成器

    Yields:
        str: SSE 格式字符串
    """
    parser = SDKMessageParser(message_generator)
    async for event in parser.parse():
        yield event


# 保留旧的事件类以保持兼容性
from dataclasses import dataclass


@dataclass
class AnthropicEvent:
    """Anthropic 标准事件（兼容）"""
    type: str
    data: Dict[str, Any]


def event_to_sse(event: AnthropicEvent) -> str:
    """
    将 AnthropicEvent 转换为 SSE 格式（兼容接口）

    Args:
        event: AnthropicEvent

    Returns:
        str: SSE 格式字符串
    """
    data = {
        "type": event.type,
        **event.data
    }
    return f"event: {event.type}\ndata: {json.dumps(data)}\n\n"