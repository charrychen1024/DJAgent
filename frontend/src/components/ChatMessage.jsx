import React from 'react';
import PropTypes from 'prop-types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FormCardBubble from './FormCardBubble';
import { MessageBlockType } from '../utils/messageTypes';
import ThinkingBlock from './ThinkingBlock';
import ToolCallCard from './ToolCallCard';
import ToolResultCard from './ToolResultCard';
import './ChatMessage.css';

/**
 * ChatMessage Component
 *
 * Universal message component that supports multiple message types:
 * - text: Plain text with markdown support
 * - form_card: Structured form for user input
 * - summary_card: Task summary/conclusion
 *
 * @component
 * @param {Object} props
 * @param {Object} props.message - Message object
 * @param {string} props.message.type - Message type (text, form_card, summary_card)
 * @param {string} props.message.sender - Who sent the message (user, agent, system)
 * @param {string} props.message.timestamp - ISO timestamp
 * @param {Function} props.onFormSubmit - Callback when form is submitted
 * @param {Function} props.onFormCancel - Callback when form is cancelled
 * @param {Function} props.onFormModify - Callback when form modify is requested
 * @param {string} props.className - Additional CSS classes
 */
const ChatMessage = ({
  message,
  onFormSubmit,
  onFormCancel,
  onFormModify,
  className = ''
}) => {
  // Handle undefined or null message
  if (!message) {
    return null;
  }

  const {
    type = 'text',
    sender = 'agent',
    timestamp,
    content,
    schema,
    form_id,
    task_id,
    title,
    summary,
    status,
    data,
    files = [],
    message: messageText // For backward compatibility with old message structure
  } = message;

  // For backward compatibility - 只有非数组时才使用
  const displayContent = !Array.isArray(content) ? (content || messageText) : '';

  // Format timestamp
  const formatTime = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${hours}:${minutes}`;
    } catch {
      return isoString;
    }
  };

  const baseClass = `chat-message chat-message--${sender} chat-message--${type}`;
  const senderLabel = sender === 'user' ? '👤 我' : sender === 'system' ? '⚙️ 系统' : '🤖 Agent';

  // 分离内容：思考过程和工具调用在气泡外，正文在气泡内
  const thinkingBlocks = []
  const toolUseBlocks = []
  const textBlocks = []

  if (Array.isArray(content)) {
    content.forEach(block => {
      if (block.type === 'thinking') {
        thinkingBlocks.push(block)
      } else if (block.type === 'tool_use') {
        toolUseBlocks.push(block)
      } else if (block.type === 'text') {
        textBlocks.push(block)
      }
    })
  }

  return (
    <div className={`${baseClass} ${className}`}>
      <div className="message-header">
        <span className="message-sender">{senderLabel}</span>
        {timestamp && <span className="message-timestamp">{formatTime(timestamp)}</span>}
      </div>

      <div className="message-body">
        {/* 思考过程 - 放在消息气泡上方 */}
        {thinkingBlocks.length > 0 && (
          <div className="thinking-blocks">
            {thinkingBlocks.map((block, index) => (
              <ThinkingBlock
                key={`thinking-${index}`}
                thinking={block.thinking}
                signature={block.signature}
              />
            ))}
          </div>
        )}

        {/* 工具调用 - 放在消息气泡上方，每个工具一行 */}
        {toolUseBlocks.length > 0 && (
          <div className="tool-blocks">
            {toolUseBlocks.map((block, index) => (
              <ToolCallCard
                key={`tool-${index}`}
                toolUseId={block.id}
                name={block.name}
                input={block.input}
              />
            ))}
          </div>
        )}

        {/* Text message - 使用消息气泡样式 */}
        {(type === 'text' || textBlocks.length > 0) && (
          <div className="message-content message-text">
            {sender === 'user' ? (
              <>
                {files && files.length > 0 && (
                  <div className="message-files">
                    {files.map((file, idx) => (
                      <div key={idx} className="message-file">
                        <span className="file-icon">📄</span>
                        <span className="file-name">{typeof file === 'string' ? file : file.name}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-content">{displayContent}</div>
              </>
            ) : (
              <div className="markdown-content">
                {/* 有 text block 时渲染 text blocks，否则渲染原始内容 */}
                {textBlocks.length > 0 ? (
                  textBlocks.map((block, index) => (
                    <div key={`text-${index}`} className="text-block">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {block.text}
                      </ReactMarkdown>
                    </div>
                  ))
                ) : (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {displayContent}
                  </ReactMarkdown>
                )}
              </div>
            )}
          </div>
        )}

        {/* Form card message */}
        {type === 'form_card' && schema && (
          <FormCardBubble
            schema={schema}
            sender={sender}
            timestamp={timestamp}
            onSubmit={(formData) => onFormSubmit?.(formData, form_id, task_id)}
            onCancel={() => onFormCancel?.(form_id, task_id)}
            onModify={() => onFormModify?.(form_id, task_id)}
          />
        )}

        {/* Summary card message */}
        {type === 'summary_card' && (
          <div className="message-content message-summary">
            <div className="summary-header">
              <h3 className="summary-title">{title}</h3>
              <span className={`summary-status summary-status--${status}`}>
                {status === 'completed' && '✓ 完成'}
                {status === 'pending' && '⏳ 待处理'}
                {status === 'failed' && '✗ 失败'}
              </span>
            </div>
            <p className="summary-text">{summary}</p>
            {data && Object.keys(data).length > 0 && (
              <div className="summary-data">
                {Object.entries(data).map(([key, value]) => (
                  <div key={key} className="summary-item">
                    <span className="item-key">{key}:</span>
                    <span className="item-value">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Unknown message type fallback */}
        {!['text', 'form_card', 'summary_card'].includes(type) && (
          <div className="message-content message-unknown">
            <p>未知消息类型: {type}</p>
          </div>
        )}
      </div>
    </div>
  );
};

ChatMessage.propTypes = {
  message: PropTypes.shape({
    type: PropTypes.oneOf(['text', 'form_card', 'summary_card']),
    sender: PropTypes.oneOf(['user', 'agent', 'system']),
    timestamp: PropTypes.string,
    content: PropTypes.string,
    message: PropTypes.string, // backward compatibility
    schema: PropTypes.object,
    form_id: PropTypes.string,
    task_id: PropTypes.string,
    title: PropTypes.string,
    summary: PropTypes.string,
    status: PropTypes.oneOf(['pending', 'completed', 'failed']),
    data: PropTypes.object,
    files: PropTypes.array
  }),
  onFormSubmit: PropTypes.func,
  onFormCancel: PropTypes.func,
  onFormModify: PropTypes.func,
  className: PropTypes.string
};

ChatMessage.defaultProps = {
  message: null,
  onFormSubmit: () => {},
  onFormCancel: () => {},
  onFormModify: () => {},
  className: ''
};

export default ChatMessage;
