"""
Claude SDK 消息解析器 - 将 Claude SDK 原生消息转换为 Anthropic 标准事件流

提供统一的接口将 SDK 的消息格式转换为标准的事件流格式，
支持 TextBlock, ThinkingBlock, ToolUseBlock, ImageBlock 等多种内容块类型。
"""

import logging
from typing import AsyncIterator, Any, Dict, Optional, List, Union
from dataclasses import dataclass

# Claude SDK 类型导入
from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

logger = logging.getLogger(__name__)


# ============ 事件类型定义 ============

@dataclass
class AnthropicEvent:
    """Anthropic 标准事件"""
    type: str
    data: Dict[str, Any]


@dataclass
class TextEvent(AnthropicEvent):
    """文本事件"""
    def __init__(self, text: str, index: int = 0):
        super().__init__(
            type="content_block_delta",
            data={
                "delta": {"type": "text_delta", "text": text},
                "index": index
            }
        )


@dataclass
class ThinkingEvent(AnthropicEvent):
    """思考事件"""
    def __init__(self, thinking: str, index: int = 0):
        super().__init__(
            type="content_block_delta",
            data={
                "delta": {"type": "thinking_delta", "thinking": thinking},
                "index": index
            }
        )


@dataclass
class ToolUseEvent(AnthropicEvent):
    """工具调用事件"""
    def __init__(self, tool_name: str, tool_input: Dict[str, Any], tool_id: str, index: int = 0):
        super().__init__(
            type="content_block_delta",
            data={
                "delta": {
                    "type": "tool_use_delta",
                    "name": tool_name,
                    "input": tool_input,
                    "tool_use_id": tool_id
                },
                "index": index
            }
        )


@dataclass
class ToolResultEvent(AnthropicEvent):
    """工具结果事件"""
    def __init__(self, tool_id: str, content: str, is_error: bool = False):
        super().__init__(
            type="content_block",
            data={
                "type": "tool_result",
                "id": tool_id,
                "content": content,
                "is_error": is_error
            }
        )


@dataclass
class MessageStartEvent(AnthropicEvent):
    """消息开始事件"""
    def __init__(self, message_id: str, role: str = "assistant"):
        super().__init__(
            type="message_start",
            data={
                "message": {
                    "id": message_id,
                    "type": "message",
                    "role": role,
                    "content": [],
                    "model": "",
                    "stop_reason": None,
                    "stop_sequence": None
                }
            }
        )


@dataclass
class MessageDeltaEvent(AnthropicEvent):
    """消息增量事件"""
    def __init__(self, stop_reason: Optional[str] = None, stop_sequence: Optional[str] = None):
        super().__init__(
            type="message_delta",
            data={
                "delta": {"stop_reason": stop_reason, "stop_sequence": stop_sequence},
                "usage": {"output_tokens": 0}
            }
        )


@dataclass
class MessageStopEvent(AnthropicEvent):
    """消息结束事件"""
    def __init__(self):
        super().__init__(
            type="message_stop",
            data={}
        )


# ============ 消息解析器 ============

class SDKMessageParser:
    """
    Claude SDK 消息解析器
    
    将 Claude SDK 原生消息转换为 Anthropic 标准事件流。
    
    Attributes:
        message_generator: 消息生成器（SDK 的 receive_response）
        event_generator: 事件生成器（用于生成事件 ID 等）
    """
    
    def __init__(self, message_generator, event_generator = None):
        """
        初始化消息解析器
        
        Args:
            message_generator: 消息生成器（异步迭代器）
            event_generator: 可选的事件生成器（用于生成唯一 ID）
        """
        self.message_generator = message_generator
        self.event_generator = event_generator
        self._message_count = 0
        logger.info("[SDKMessageParser] 初始化完成")
    
    async def parse(self) -> AsyncIterator[AnthropicEvent]:
        """
        异步迭代器，返回 Anthropic 标准事件流
        
        Yields:
            AnthropicEvent: 标准事件
        """
        logger.info("[SDKMessageParser] 开始解析消息")
        
        async for msg in self.message_generator:
            self._message_count += 1
            logger.debug(f"[SDKMessageParser] 处理消息 #{self._message_count}: {type(msg).__name__}")
            
            if isinstance(msg, AssistantMessage):
                async for event in self._parse_assistant_message(msg):
                    yield event
            elif isinstance(msg, ResultMessage):
                async for event in self._parse_result_message(msg):
                    yield event
            else:
                logger.warning(f"[SDKMessageParser] 未知消息类型: {type(msg).__name__}")
        
        logger.info(f"[SDKMessageParser] 解析完成，共处理 {self._message_count} 条消息")
    
    async def _parse_assistant_message(self, msg: AssistantMessage) -> AsyncIterator[AnthropicEvent]:
        """
        解析 AssistantMessage
        
        Args:
            msg: AssistantMessage 对象
            
        Yields:
            AnthropicEvent: 解析后的事件
        """
        # 生成消息 ID
        message_id = self._generate_id()
        
        # 发送消息开始事件
        yield MessageStartEvent(message_id=message_id, role="assistant")
        
        # 遍历所有 content blocks
        if hasattr(msg, 'content') and hasattr(msg.content, '__iter__'):
            index = 0
            for block in msg.content:
                if self._is_thinking_block(block):
                    async for event in self._parse_thinking_block(block, index):
                        yield event
                    index += 1
                elif self._is_text_block(block):
                    async for event in self._parse_text_block(block, index):
                        yield event
                    index += 1
                elif self._is_tool_use_block(block):
                    async for event in self._parse_tool_use_block(block, index):
                        yield event
                    index += 1
                elif self._is_image_block(block):
                    async for event in self._parse_image_block(block, index):
                        yield event
                    index += 1
                else:
                    logger.warning(f"[SDKMessageParser] 未知 block 类型: {type(block).__name__}")
        
        # 发送消息结束事件
        yield MessageDeltaEvent(stop_reason="end_turn", stop_sequence=None)
        yield MessageStopEvent()
    
    def _is_thinking_block(self, block) -> bool:
        """
        判断是否是思考块
        
        Args:
            block: 内容块
            
        Returns:
            bool: 是否是思考块
        """
        # 检查是否有 thinking 相关属性
        has_thinking = hasattr(block, 'thinking') or hasattr(block, 'thinking_text')
        # 检查 type 是否为 thinking
        has_type = hasattr(block, 'type') and block.type == 'thinking'
        
        return has_thinking or has_type
    
    def _is_text_block(self, block) -> bool:
        """
        判断是否是文本块
        
        Args:
            block: 内容块
            
        Returns:
            bool: 是否是文本块
        """
        # TextBlock 实例
        if isinstance(block, TextBlock):
            return True
        # 检查是否有 text 属性且 type 为 text
        if hasattr(block, 'type') and block.type == 'text':
            return True
        # 检查是否有 text 属性且没有其他特殊类型
        if hasattr(block, 'text') and not self._is_tool_use_block(block):
            return True
        
        return False
    
    def _is_tool_use_block(self, block) -> bool:
        """
        判断是否是工具调用块
        
        Args:
            block: 内容块
            
        Returns:
            bool: 是否是工具调用块
        """
        # 检查 type 属性
        if hasattr(block, 'type') and block.type == 'tool_use':
            return True
        # 检查是否有 name 和 input 属性（工具调用的特征）
        if hasattr(block, 'name') and hasattr(block, 'input'):
            return True
        # 检查是否是 ToolUseBlock 类型
        return type(block).__name__ == 'ToolUseBlock'
    
    def _is_image_block(self, block) -> bool:
        """
        判断是否是图片块
        
        Args:
            block: 内容块
            
        Returns:
            bool: 是否是图片块
        """
        # 检查 type 属性
        if hasattr(block, 'type') and block.type == 'image':
            return True
        # 检查是否有 source 属性（图片通常有 source）
        if hasattr(block, 'source'):
            return True
        # 检查是否是 ImageBlock 类型
        return type(block).__name__ == 'ImageBlock'
    
    async def _parse_thinking_block(self, block, index: int) -> AsyncIterator[AnthropicEvent]:
        """
        解析思考块
        
        Args:
            block: 思考块
            index: 块索引
            
        Yields:
            AnthropicEvent: 思考事件
        """
        # 获取思考内容
        thinking = ""
        if hasattr(block, 'thinking'):
            thinking = block.thinking
        elif hasattr(block, 'thinking_text'):
            thinking = block.thinking_text
        elif hasattr(block, 'text'):
            thinking = block.text
        
        logger.debug(f"[SDKMessageParser] 思考块 #{index}: {thinking[:50]}...")
        
        yield ThinkingEvent(thinking=thinking, index=index)
    
    async def _parse_text_block(self, block, index: int) -> AsyncIterator[AnthropicEvent]:
        """
        解析文本块
        
        Args:
            block: 文本块
            index: 块索引
            
        Yields:
            AnthropicEvent: 文本事件
        """
        # 获取文本内容
        text = ""
        if hasattr(block, 'text'):
            text = block.text
        
        logger.debug(f"[SDKMessageParser] 文本块 #{index}: {text[:50]}...")
        
        yield TextEvent(text=text, index=index)
    
    async def _parse_tool_use_block(self, block, index: int) -> AsyncIterator[AnthropicEvent]:
        """
        解析工具调用块
        
        Args:
            block: 工具调用块
            index: 块索引
            
        Yields:
            AnthropicEvent: 工具调用事件
        """
        # 获取工具名称
        tool_name = ""
        if hasattr(block, 'name'):
            tool_name = block.name
        
        # 获取工具输入
        tool_input = {}
        if hasattr(block, 'input'):
            tool_input = block.input
        
        # 获取工具 ID
        tool_id = ""
        if hasattr(block, 'id'):
            tool_id = block.id
        else:
            tool_id = self._generate_id()
        
        logger.debug(f"[SDKMessageParser] 工具调用块 #{index}: {tool_name}")
        
        yield ToolUseEvent(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_id=tool_id,
            index=index
        )
    
    async def _parse_image_block(self, block, index: int) -> AsyncIterator[AnthropicEvent]:
        """
        解析图片块
        
        Args:
            block: 图片块
            index: 块索引
            
        Yields:
            AnthropicEvent: 图片事件（转换为文本描述）
        """
        # 提取图片信息
        image_info = ""
        
        if hasattr(block, 'source'):
            source = block.source
            if hasattr(source, 'type'):
                image_info = f"[图片: {source.type}]"
            elif hasattr(source, 'url'):
                image_info = f"[图片: {source.url}]"
        
        if hasattr(block, 'type'):
            image_info = f"[图片类型: {block.type}]"
        
        logger.debug(f"[SDKMessageParser] 图片块 #{index}: {image_info}")
        
        # 图片块转换为文本事件
        yield TextEvent(text=image_info, index=index)
    
    async def _parse_result_message(self, msg: ResultMessage) -> AsyncIterator[AnthropicEvent]:
        """
        解析 ResultMessage（工具结果）
        
        Args:
            msg: ResultMessage 对象
            
        Yields:
            AnthropicEvent: 工具结果事件
        """
        # 获取工具 ID
        tool_id = ""
        if hasattr(msg, 'tool_use_id'):
            tool_id = msg.tool_use_id
        elif hasattr(msg, 'id'):
            tool_id = msg.id
        else:
            tool_id = self._generate_id()
        
        # 获取结果内容
        content = ""
        if hasattr(msg, 'content'):
            content = msg.content
        elif hasattr(msg, 'result'):
            content = msg.result
        elif hasattr(msg, 'output'):
            content = msg.output
        
        # 判断是否是错误
        is_error = False
        if hasattr(msg, 'is_error'):
            is_error = msg.is_error
        elif hasattr(msg, 'error'):
            is_error = True
            if isinstance(msg.error, dict):
                content = str(msg.error.get('message', content))
            else:
                content = str(msg.error)
        
        # 获取子类型
        subtype = ""
        if hasattr(msg, 'subtype'):
            subtype = msg.subtype
        
        logger.debug(f"[SDKMessageParser] 工具结果: tool_id={tool_id}, subtype={subtype}, is_error={is_error}")
        
        yield ToolResultEvent(
            tool_id=tool_id,
            content=content,
            is_error=is_error
        )
    
    def _generate_id(self) -> str:
        """
        生成唯一 ID
        
        Returns:
            str: 唯一 ID
        """
        import uuid
        return f"msg_{uuid.uuid4().hex[:16]}"


# ============ 便捷函数 ============

async def parse_sdk_messages(message_generator) -> AsyncIterator[AnthropicEvent]:
    """
    便捷函数：解析 SDK 消息为标准事件流
    
    Args:
        message_generator: SDK 消息生成器
        
    Yields:
        AnthropicEvent: 标准事件
    """
    parser = SDKMessageParser(message_generator)
    async for event in parser.parse():
        yield event


# ============ 事件序列化 ============

def event_to_sse(event: AnthropicEvent) -> str:
    """
    将事件转换为 SSE 格式
    
    Args:
        event: AnthropicEvent
        
    Returns:
        str: SSE 格式字符串
    """
    import json
    
    data = {
        "type": event.type,
        **event.data
    }
    
    return f"data: {json.dumps(data)}\n\n"


async def stream_events_as_sse(event_generator) -> AsyncIterator[str]:
    """
    将事件流转换为 SSE 格式流
    
    Args:
        event_generator: 事件生成器
        
    Yields:
        str: SSE 格式字符串
    """
    async for event in event_generator:
        yield event_to_sse(event)