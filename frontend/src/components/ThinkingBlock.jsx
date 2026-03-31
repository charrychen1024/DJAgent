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

  if (!thinking) return null;

  return (
    <div className={`thinking-block ${isExpanded ? 'expanded' : ''}`}>
      <div
        className="thinking-badge"
        onClick={() => setIsExpanded(!isExpanded)}
        title="点击展开思考过程"
      >
        <span className="thinking-icon">💭</span>
        <span>思考</span>
        <span className="thinking-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="thinking-content">
          <div className="thinking-text">
            {thinking}
          </div>

          {signature && (
            <div className="thinking-signature">
              ID: {signature.substring(0, 16)}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

ThinkingBlock.propTypes = {
  thinking: PropTypes.string,
  signature: PropTypes.string,
  defaultExpanded: PropTypes.bool
};

export default ThinkingBlock;
