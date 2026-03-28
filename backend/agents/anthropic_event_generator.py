"""
Anthropic 标准事件生成器

生成符合 Anthropic Messages API Streaming 规范的 SSE 事件。
"""

import json
import uuid
from typing import Any, Dict, Optional


class AnthropicEventGenerator:
    """Anthropic SSE 事件生成器"""
    
    def __init__(self, message_id: Optional[str] = None):
        """
        初始化事件生成器
        
        Args:
            message_id: 可选的自定义消息ID，默认自动生成UUID
        """
        self.message_id = message_id or str(uuid.uuid4())
        self._block_index = 0
        self._block_id_prefix = f"msg_{self.message_id[:8]}_"
    
    def _to_sse(self, event_name: str, data: Dict[str, Any]) -> str:
        """
        将事件数据转换为 SSE 格式
        
        Args:
            event_name: 事件名称
            data: 事件数据字典
            
        Returns:
            SSE 格式字符串，格式为: event: {event_name}\ndata: {json_data}\n\n
        """
        json_str = json.dumps(data, ensure_ascii=False)
        return f"event: {event_name}\ndata: {json_str}\n\n"
    
    def _generate_block_id(self) -> str:
        """生成内容块ID"""
        block_id = f"{self._block_id_prefix}{self._block_index}"
        self._block_index += 1
        return block_id
    
    def message_start(self, role: str = "assistant") -> str:
        """
        生成 message_start 事件
        
        消息开始的信号，包含消息ID和角色信息。
        
        Args:
            role: 消息角色，默认为 "assistant"
            
        Returns:
            SSE 格式的事件字符串
        """
        data = {
            "type": "message_start",
            "message": {
                "id": self.message_id,
                "type": "message",
                "role": role,
                "content": [],
                "model": "",
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            }
        }
        return self._to_sse("message_start", data)
    
    def content_block_start(self, block_type: str, block_data: Optional[Dict[str, Any]] = None) -> str:
        """
        生成 content_block_start 事件
        
        内容块开始的信号，支持的类型: thinking, text, tool_use, tool_result, image
        
        Args:
            block_type: 内容块类型 (thinking, text, tool_use, tool_result, image)
            block_data: 可选的初始块数据
            
        Returns:
            SSE 格式的事件字符串
        """
        block_id = self._generate_block_id()
        
        block_content: Dict[str, Any] = {"id": block_id, "type": block_type}
        
        # 根据类型初始化相应的字段
        if block_type == "thinking":
            block_content["thinking"] = ""
        elif block_type == "text":
            block_content["text"] = ""
        elif block_type == "tool_use":
            block_content["name"] = block_data.get("name", "") if block_data else ""
            block_content["input"] = block_data.get("input", {}) if block_data else {}
        elif block_type == "tool_result":
            block_content["tool_use_id"] = block_data.get("tool_use_id", "") if block_data else ""
            block_content["content"] = ""
            block_content["is_error"] = block_data.get("is_error", False) if block_data else False
        elif block_type == "image":
            block_content["source"] = block_data.get("source", {}) if block_data else {}
        
        data = {
            "type": "content_block_start",
            "index": self._block_index - 1,
            "content_block": block_content
        }
        return self._to_sse("content_block_start", data)
    
    def content_block_delta(self, delta_type: str, delta_data: Dict[str, Any]) -> str:
        """
        生成 content_block_delta 事件
        
        内容块增量更新的信号，支持的类型: thinking_delta, text_delta, input_json_delta, signature_delta
        
        Args:
            delta_type: 增量类型 (thinking_delta, text_delta, input_json_delta, signature_delta)
            delta_data: 增量数据
            
        Returns:
            SSE 格式的事件字符串
        """
        delta_content: Dict[str, Any] = {"type": delta_type}
        
        if delta_type == "thinking_delta":
            delta_content["thinking"] = delta_data.get("text", "")
        elif delta_type == "text_delta":
            delta_content["text"] = delta_data.get("text", "")
        elif delta_type == "input_json_delta":
            delta_content["partial_json"] = delta_data.get("partial_json", "")
        elif delta_type == "signature_delta":
            delta_content["signature"] = delta_data.get("signature", "")
        
        data = {
            "type": "content_block_delta",
            "index": self._block_index - 1,
            "delta": delta_content
        }
        return self._to_sse("content_block_delta", data)
    
    def thinking_delta(self, thinking: str) -> str:
        """
        生成 thinking_delta 事件
        
        Thinking 内容的增量更新。
        
        Args:
            thinking: thinking 内容增量
            
        Returns:
            SSE 格式的事件字符串
        """
        return self.content_block_delta("thinking_delta", {"text": thinking})
    
    def text_delta(self, text: str) -> str:
        """
        生成 text_delta 事件
        
        Text 内容的增量更新。
        
        Args:
            text: text 内容增量
            
        Returns:
            SSE 格式的事件字符串
        """
        return self.content_block_delta("text_delta", {"text": text})
    
    def signature_delta(self, signature: str) -> str:
        """
        生成 signature_delta 事件
        
        签名的增量更新。
        
        Args:
            signature: signature 内容
            
        Returns:
            SSE 格式的事件字符串
        """
        return self.content_block_delta("signature_delta", {"signature": signature})
    
    def input_json_delta(self, partial_json: str) -> str:
        """
        生成 input_json_delta 事件
        
        Tool input JSON 的增量更新。
        
        Args:
            partial_json: 部分 JSON 字符串
            
        Returns:
            SSE 格式的事件字符串
        """
        return self.content_block_delta("input_json_delta", {"partial_json": partial_json})
    
    def content_block_stop(self) -> str:
        """
        生成 content_block_stop 事件
        
        内容块结束的信号。
        
        Returns:
            SSE 格式的事件字符串
        """
        data = {
            "type": "content_block_stop",
            "index": self._block_index - 1
        }
        return self._to_sse("content_block_stop", data)
    
    def tool_use_start(self, tool_name: str, tool_input: Optional[Dict[str, Any]] = None) -> str:
        """
        生成 tool_use 事件 (content_block_start)
        
        工具调用的开始事件。
        
        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数
            
        Returns:
            SSE 格式的事件字符串
        """
        return self.content_block_start("tool_use", {
            "name": tool_name,
            "input": tool_input or {}
        })
    
    def tool_result(self, tool_use_id: str, content: str, is_error: bool = False) -> str:
        """
        生成 tool_result 事件 (content_block_start + content_block_delta)
        
        工具执行结果的完成事件。
        
        Args:
            tool_use_id: 对应的 tool_use 的 ID
            content: 工具返回的内容
            is_error: 是否为错误结果
            
        Returns:
            SSE 格式的事件字符串
        """
        # 生成 content_block_start
        start_event = self.content_block_start("tool_result", {
            "tool_use_id": tool_use_id,
            "is_error": is_error
        })
        
        # 生成 content_block_delta
        delta_event = self.content_block_delta("text_delta", {"text": content})
        
        # 生成 content_block_stop
        stop_event = self.content_block_stop()
        
        return start_event + delta_event + stop_event
    
    def message_delta(self, stop_reason: Optional[str] = None, usage: Optional[Dict[str, int]] = None) -> str:
        """
        生成 message_delta 事件
        
        消息级别的增量更新，包含停止原因和 token 使用量。
        
        Args:
            stop_reason: 停止原因 (end_turn, max_tokens, stop_sequence)
            usage: token 使用量 {"output_tokens": int, "input_tokens": int}
            
        Returns:
            SSE 格式的事件字符串
        """
        delta_data = {
            "type": "message_delta",
            "delta": {
                "stop_reason": stop_reason,
                "stop_sequence": None
            },
            "usage": usage or {
                "output_tokens": 0,
                "input_tokens": 0
            }
        }
        return self._to_sse("message_delta", delta_data)
    
    def message_stop(self) -> str:
        """
        生成 message_stop 事件
        
        消息结束的信号。
        
        Returns:
            SSE 格式的事件字符串
        """
        data = {
            "type": "message_stop"
        }
        return self._to_sse("message_stop", data)
    
    def ping(self) -> str:
        """
        生成 ping 事件
        
        用于保持连接的 ping 事件。
        
        Returns:
            SSE 格式的事件字符串
        """
        data = {"type": "ping"}
        return self._to_sse("ping", data)


# 便捷函数：创建默认事件生成器
def create_event_generator(message_id: Optional[str] = None) -> AnthropicEventGenerator:
    """
    创建事件生成器的便捷函数
    
    Args:
        message_id: 可选的自定义消息ID
        
    Returns:
        AnthropicEventGenerator 实例
    """
    return AnthropicEventGenerator(message_id)


if __name__ == "__main__":
    # 测试示例
    generator = AnthropicEventGenerator()
    
    print("=== 测试 message_start ===")
    print(generator.message_start())
    
    print("=== 测试 content_block_start (text) ===")
    print(generator.content_block_start("text"))
    
    print("=== 测试 text_delta ===")
    print(generator.text_delta("你好"))
    print(generator.text_delta("世界！"))
    
    print("=== 测试 content_block_stop ===")
    print(generator.content_block_stop())
    
    print("=== 测试 tool_use_start ===")
    print(generator.tool_use_start("calculator", {"operation": "add", "a": 1, "b": 2}))
    
    print("=== 测试 tool_result ===")
    print(generator.tool_result("tool_123", "结果是 3", is_error=False))
    
    print("=== 测试 message_delta ===")
    print(generator.message_delta(stop_reason="end_turn", usage={"output_tokens": 50, "input_tokens": 100}))
    
    print("=== 测试 message_stop ===")
    print(generator.message_stop())