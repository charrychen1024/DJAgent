/**
 * Anthropic 标准流式接收 Hook
 * 
 * 完整支持 thinking/tool_use/text/tool_result 事件
 */

import { useState, useCallback, useRef } from 'react';
import { MessageBlockType, parseSSEEvent } from '../utils/messageTypes';

export function useAnthropicStream(endpoint = '/api/chat/stream') {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const currentMessageRef = useRef(null);
  const contentBlocksRef = useRef([]);
  
  const sendMessage = useCallback(async (text, employeeId, username) => {
    setIsStreaming(true);
    
    // 1. 添加用户消息
    const userMsg = {
      role: 'user',
      content: [{
        type: MessageBlockType.TEXT,
        text: text
      }],
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    
    // 2. 创建 Assistant 占位消息
    const assistantMsg = {
      id: null,
      role: 'assistant',
      content: [],
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, assistantMsg]);
    currentMessageRef.current = assistantMsg;
    contentBlocksRef.current = [];
    
    try {
      // 3. 发起流式请求
      const response = await fetch(`http://localhost:5005${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          employee_id: employeeId,
          username
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      
      // 4. 读取 SSE 流
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEventType = null;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        
        for (const line of lines) {
          // 处理 SSE 格式: event: xxx\ndata: xxx
          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6).trim());
              handleEvent(currentEventType, data);
            } catch (e) {
              console.error('解析 SSE 数据失败:', e);
            }
          }
        }
      }
      
      setIsStreaming(false);
    } catch (error) {
      console.error('流式接收失败:', error);
      setIsStreaming(false);
      
      // 添加错误消息
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        lastMsg.content.push({
          type: 'error',
          text: `错误: ${error.message}`
        });
        return newMessages;
      });
    }
  }, [endpoint]);
  
  const handleEvent = (eventType, eventData) => {
    const parsed = parseSSEEvent(eventType, eventData);
    
    switch (parsed.type) {
      case 'message_start':
        // 消息开始 - 设置消息 ID
        if (currentMessageRef.current) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            lastMsg.id = eventData.message?.id;
            return newMessages;
          });
        }
        break;
        
      case 'content_block_start':
        // 内容块开始 - 创建新的 content block
        if (currentMessageRef.current) {
          const newBlock = {
            type: parsed.contentBlock.type,
            index: parsed.index,
            ...parsed.contentBlock
          };
          contentBlocksRef.current[parsed.index] = newBlock;
          
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            lastMsg.content.push(newBlock);
            return newMessages;
          });
        }
        break;
        
      case 'content_block_delta':
        // 内容块增量 - 更新当前 block
        if (currentMessageRef.current) {
          const blockIndex = parsed.index;
          const delta = parsed.delta;
          
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            const block = lastMsg.content[blockIndex];
            
            if (block) {
              // 根据增量类型更新
              if (delta.type === 'text_delta' && block.type === MessageBlockType.TEXT) {
                block.text = (block.text || '') + (delta.text || '');
              } else if (delta.type === 'thinking_delta' && block.type === MessageBlockType.THINKING) {
                block.thinking = (block.thinking || '') + (delta.thinking || '');
              } else if (delta.type === 'signature_delta' && block.type === MessageBlockType.THINKING) {
                block.signature = (block.signature || '') + (delta.signature || '');
              } else if (delta.type === 'input_json_delta' && block.type === MessageBlockType.TOOL_USE) {
                // 工具输入增量
                try {
                  block.input = { ...block.input, ...JSON.parse(delta.partial_json || '{}') };
                } catch {}
              }
            }
            
            return newMessages;
          });
        }
        break;
        
      case 'message_delta':
        // 消息级别更新
        if (parsed.delta?.stop_reason === 'end_turn') {
          // 对话轮次结束
        }
        break;
        
      case 'message_stop':
        // 消息结束
        currentMessageRef.current = null;
        contentBlocksRef.current = [];
        break;
    }
  };
  
  const clearMessages = useCallback(() => {
    setMessages([]);
    currentMessageRef.current = null;
    contentBlocksRef.current = [];
  }, []);
  
  return {
    messages,
    isStreaming,
    sendMessage,
    clearMessages
  };
}
