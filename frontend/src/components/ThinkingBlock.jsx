import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './ThinkingBlock.css';

/**
 * Thinking Block 组件 - 简约版
 *
 * 显示 AI 思考过程，使用行内徽章样式
 */
const ThinkingBlock = ({ thinking, signature, defaultExpanded = false }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // 只显示前50字符作为预览
  const previewText = thinking.length > 50
    ? thinking.substring(0, 50) + '...'
    : thinking;

  return (
    <div className={`thinking-block ${isExpanded ? 'expanded' : ''}`}>
      <div
        className="thinking-badge"
        onClick={() => setIsExpanded(!isExpanded)}
        title={thinking}
      >
        <span className="thinking-icon">💭</span>
        <span>思考</span>
        <span className="thinking-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="thinking-content">
          <pre style={{
            margin: '8px 0',
            padding: '8px',
            background: 'var(--bg-gray, #f5f5f5)',
            borderRadius: '4px',
            fontSize: '12px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}>
            {thinking}
          </pre>

          {signature && (
            <div style={{
              fontSize: '10px',
              color: 'var(--text-secondary, #8c8c8c)',
              marginTop: '4px'
            }}>
              ID: {signature.substring(0, 16)}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

ThinkingBlock.propTypes = {
  thinking: PropTypes.string.isRequired,
  signature: PropTypes.string,
  defaultExpanded: PropTypes.bool
};

export default ThinkingBlock;
