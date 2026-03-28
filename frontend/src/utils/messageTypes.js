/**
 * Anthropic 标准消息类型
 */

export const MessageBlockType = {
  THINKING: 'thinking',
  TEXT: 'text',
  TOOL_USE: 'tool_use',
  TOOL_RESULT: 'tool_result',
  IMAGE: 'image'
};

/**
 * 前端渲染组件映射
 */
export const BlockComponentMap = {
  [MessageBlockType.THINKING]: 'ThinkingBlock',
  [MessageBlockType.TEXT]: 'TextBlock',
  [MessageBlockType.TOOL_USE]: 'ToolCallCard',
  [MessageBlockType.TOOL_RESULT]: 'ToolResultCard',
  [MessageBlockType.IMAGE]: 'ImageBlock'
};

/**
 * SSE 事件类型
 */
export const SSEEventType = {
  MESSAGE_START: 'message_start',
  CONTENT_BLOCK_START: 'content_block_start',
  CONTENT_BLOCK_DELTA: 'content_block_delta',
  CONTENT_BLOCK_STOP: 'content_block_stop',
  MESSAGE_DELTA: 'message_delta',
  MESSAGE_STOP: 'message_stop',
  ERROR: 'error'
};

/**
 * 解析 SSE 事件
 * @param {string} eventType - 事件类型
 * @param {object} data - 事件数据
 * @returns {object} 解析后的消息块
 */
export function parseSSEEvent(eventType, data) {
  switch (eventType) {
    case SSEEventType.MESSAGE_START:
      return { type: 'message_start', message: data.message };
      
    case SSEEventType.CONTENT_BLOCK_START:
      return { type: 'content_block_start', contentBlock: data.content_block, index: data.index };
      
    case SSEEventType.CONTENT_BLOCK_DELTA:
      return { type: 'content_block_delta', delta: data.delta, index: data.index };
      
    case SSEEventType.CONTENT_BLOCK_STOP:
      return { type: 'content_block_stop', index: data.index };
      
    case SSEEventType.MESSAGE_DELTA:
      return { type: 'message_delta', delta: data.delta };
      
    case SSEEventType.MESSAGE_STOP:
      return { type: 'message_stop' };
      
    case SSEEventType.ERROR:
      return { type: 'error', error: data.error };
      
    default:
      return { type: 'unknown' };
  }
}
